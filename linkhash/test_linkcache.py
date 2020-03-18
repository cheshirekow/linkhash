"""
Configure and build the test project and verify that the linkcache works
as expected.
"""

import argparse
import difflib
import io
import logging
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import tempfile

logger = logging.getLogger(__name__)

PROJECT_FILES = [
    "bar.cc",
    "CMakeLists.txt",
    "foo.cc",
    "main.cc"
]


EXPECT_ONE = """\
[1/6] Building CXX object CMakeFiles/prog.dir/main.cc.o
[2/6] Building CXX object CMakeFiles/foo.dir/foo.cc.o
[3/6] Linking CXX shared library libfoo.so
DEBUG:__main__:Output of command does not yet exist
DEBUG:__main__:Cache miss, executing subcommand
[4/6] Building CXX object CMakeFiles/bar.dir/bar.cc.o
[5/6] Linking CXX shared library libbar.so
DEBUG:__main__:Output of command does not yet exist
DEBUG:__main__:Cache miss, executing subcommand
[6/6] Linking CXX executable prog
DEBUG:__main__:Output of command does not yet exist
DEBUG:__main__:Cache miss, executing subcommand
"""

EXPECT_TWO = """\
[1/4] Building CXX object CMakeFiles/foo.dir/foo.cc.o
[2/4] Linking CXX shared library libfoo.so
DEBUG:__main__:Input file has changed CMakeFiles/foo.dir/foo.cc.o
DEBUG:__main__:Cache miss, executing subcommand
[3/4] Linking CXX shared library libbar.so
DEBUG:__main__:Input object is cache OK: libfoo.so
DEBUG:__main__:Using link-cache of libbar.so
DEBUG:__main__:Cache hit, touching libbar.so
[4/4] Linking CXX executable prog
DEBUG:__main__:Input object is cache OK: libbar.so
DEBUG:__main__:Input object is cache OK: libfoo.so
DEBUG:__main__:Using link-cache of prog
DEBUG:__main__:Cache hit, touching prog
"""

def sortlines(content):
  ninja_prefix = re.compile(r"\[\d+/\d+\] (.*)")

  outlines = []
  for line in content.split("\n"):
    ninja_match = ninja_prefix.match(line)
    if ninja_match:
      outlines.append(ninja_match.group(1))
      continue
    outlines.append(line)

  return "\n".join(sorted(outlines))

def assert_equal(expected, actual):
  if sortlines(expected) == sortlines(actual):
    return

  stream = io.StringIO()
  stream.write("Expected String:\n")
  stream.write("================\n")
  stream.write(expected)
  stream.write("\n")
  stream.write("Actual String:\n")
  stream.write("==============\n")
  stream.write(actual)
  stream.write("\n")
  stream.write("Delta:\n")
  stream.write("======\n")
  for line in difflib.unified_diff(expected.split("\n"), actual.split("\n")):
    stream.write(line)
    if not line.endswith("\n"):
      stream.write("\n")
  raise AssertionError(stream.getvalue())


def touch(filepath, times=None):
  with open(filepath, 'a'):
    os.utime(filepath, times)


def runtest(tmpdir, args):
  srcdir = os.path.join(tmpdir, "src")
  os.makedirs(srcdir)
  for filename in PROJECT_FILES:
    shutil.copyfile(
        os.path.join(args.project_template, filename),
        os.path.join(srcdir, filename))

  prefixdir = os.path.join(tmpdir, "prefix")
  tgtdir = os.path.join(prefixdir, args.pkgdir.lstrip("/"))
  os.makedirs(tgtdir)

  filenames = [
      "linkhash-config.cmake",
      "linkhash-config-version.cmake"
  ]

  for filename in filenames:
    # NOTE(josh): linkhash-targets.cmake exists in both directories, but we
    # want the installed version, which is in the Export/ dir, so we need to
    # check that location first.
    srcpath = os.path.join(args.bindir, filename)
    if not os.path.exists(srcpath):
      raise RuntimeError(
          "No sourcefile for {}".format(filename))
    shutil.copyfile(srcpath, os.path.join(tgtdir, filename))

  exportdir = os.path.join(args.bindir, "CMakeFiles/Export", args.pkgdir)
  for filename in os.listdir(exportdir):
    srcpath = os.path.join(exportdir, filename)
    if not os.path.exists(srcpath):
      raise RuntimeError(
          "I messed up with {}".format(filename))
    shutil.copyfile(srcpath, os.path.join(tgtdir, filename))

  bindir = os.path.join(prefixdir, "bin")
  os.makedirs(bindir)
  shutil.copyfile(args.linkhash, os.path.join(bindir, "linkhash"))
  os.chmod(os.path.join(bindir, "linkhash"), 0o755)
  shutil.copyfile(args.linkcache, os.path.join(bindir, "linkcache"))
  os.chmod(os.path.join(bindir, "linkcache"), 0o755)

  logdir = os.path.join(tmpdir, "log")
  os.makedirs(logdir)
  bindir = os.path.join(tmpdir, "build")
  os.makedirs(bindir)

  logpath0 = os.path.join(logdir, "00-cmake.log")
  with open(logpath0, "wb") as logfile:
    result = subprocess.call(
        ["cmake", "-G", "Ninja", "-DCMAKE_PREFIX_PATH={}".format(prefixdir),
         "-DENABLE_LINKCACHE=ON", "../src"], cwd=bindir,
         stdout=logfile, stderr=logfile)

  if result != 0:
    with io.open(logpath0, "r", encoding="utf-8") as logfile:
      logcontent = logfile.read()
    raise AssertionError(
        "cmake exited with non-zero status:\n" + logcontent)

  logpath1 = os.path.join(logdir, "01-ninja.log")
  with open(logpath1 , "wb") as logfile:
    result = subprocess.call(
        ["ninja", "-j", "1"], cwd=bindir, stdout=logfile, stderr=logfile)

  if result != 0:
    with io.open(logpath1, "r", encoding="utf-8") as logfile:
      logcontent = logfile.read()
    raise AssertionError(
        "ninja(1) exited with non-zero status:\n" + logcontent)

  # Try to ensure that the mtime of foo.cc is updated to something *after*
  # the output
  time.sleep(2)
  touch(os.path.join(srcdir, "foo.cc"))
  logpath2 = os.path.join(logdir, "02-ninja.log")
  with open(logpath2, "wb") as logfile:
    result = subprocess.call(
        ["ninja", "-j", "1"], cwd=bindir, stdout=logfile, stderr=logfile)

  if result != 0:
    with io.open(logpath2, "r", encoding="utf-8") as logfile:
      logcontent = logfile.read()
    raise AssertionError(
        "ninja(2) exited with non-zero status:\n" + logcontent)

  with io.open(logpath1, "r", encoding="utf-8") as infile:
    assert_equal(EXPECT_ONE, infile.read())
  with io.open(logpath2, "r", encoding="utf-8") as infile:
    assert_equal(EXPECT_TWO, infile.read())


def main():
  logging.basicConfig()
  argparser = argparse.ArgumentParser(description=__doc__)
  argparser.add_argument(
      "--log-level", default="info",
      choices=["debug", "info", "warning", "error"])
  argparser.add_argument(
      "--pkgdir", required=True,
      help="relative path in the install tree of where cmake stuff goes")
  argparser.add_argument(
      "--project-template", required=True,
      help="Path to the project template directory")
  argparser.add_argument(
      "--bindir", required=True,
      help="Path to binary directory")
  argparser.add_argument(
      "--linkhash", required=True,
      help="Path to linkhash binary")
  argparser.add_argument(
      "--linkcache", required=True,
      help="Path to linkcache binary")
  argparser.add_argument(
      "--keep-dir", action="store_true",
      help="don't delete the working tree, even if the test passes")
  args = argparser.parse_args()
  logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

  tmpdir = tempfile.mkdtemp(prefix="linkhash-")
  logger.debug("Working in %s", tmpdir)

  try:
    runtest(tmpdir, args)
    if not args.keep_dir:
      shutil.rmtree(tmpdir)
    return 0
  except AssertionError as ex:
    logger.error(ex.args[0])
  except:
    logger.exception("Internal Error:")
  logger.info(
      "Working directory was left in place at %s for debugging", tmpdir)
  return 1


if __name__ == "__main__":
  sys.exit(main())
