#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""
Wrap a link command. If the link command can be skipped due to the fact that
the output is up-to-date with respect to the inputs, then the command is
skipped and the output is touched instead.
"""

from __future__ import print_function, unicode_literals

import argparse
import collections
import hashlib
import io
import json
import logging
import os
import pathlib
import subprocess
import sys

logger = logging.getLogger(__name__)

# See: http://man7.org/linux/man-pages/man1/ld.1.html#ENVIRONMENT
KEEPENV = [
    "COLLECT_NO_DEMANGLE",
    "GNUTARGET",
    "LDEMULATION",
    "PATH",
]


def get_execspec(subcommand):
  env = dict(os.environ)

  # Remove environment variables that we know don't affect the link process
  env = collections.OrderedDict()
  for key, value in dict(os.environ).items():
    if key.startswith("LD_"):
      env[key] = value
      continue

    if key in KEEPENV:
      env[key] = value
      continue

  spec = collections.OrderedDict()
  spec["argv"] = subcommand
  spec["cwd"] = os.getcwd()
  spec["env"] = env

  hashstr = hashlib.sha1(json.dumps(spec, indent=2).encode("utf-8")).hexdigest()
  spec["hash"] = hashstr

  return spec


def find_linkhash():
  for prefix in os.environ.get("PATH", "").split(":"):
    fullpath = os.path.join(prefix, "linkhash")
    if os.path.isfile(fullpath) and os.access(fullpath, os.X_OK):
      return fullpath

  prefix = os.path.dirname(os.path.realpath(__file__))
  fullpath = os.path.join(prefix, "linkhash")
  if os.path.isfile(fullpath) and os.access(fullpath, os.X_OK):
    return fullpath

  return None


class Context(object):
  def __init__(self, subcommand):
    self.subcommand = subcommand
    self.execspec = get_execspec(subcommand)
    self.outfile = None

  def get_cacheinfopath(self):
    return self.outfile + ".cacheinfo"

  def get_apidpath(self):
    return self.outfile + ".apid"

  def cache_hit(self):
    subcommand = self.subcommand

    try:
      dasho_idx = subcommand.index("-o")
      self.outfile = outfile = subcommand[dasho_idx + 1]
    except (IndexError, ValueError):
      # The command doesn't have a "-o" in it anywhere
      logger.debug("Command doesn't have a recognizable output")
      return False

    try:
      outfile_mtime = os.path.getmtime(outfile)
    except OSError:
      # The output of the command doesn't exist, so we can't reuse it
      logger.debug("Output of command does not yet exist")
      return False

    execspec = self.execspec
    cacheinfopath = self.get_cacheinfopath()

    if not os.path.exists(cacheinfopath):
      # There is no sidecar metdata written by this script for the given
      # output file, so we can't validate the existing output and we must
      # re-execute the command
      logger.debug("Command output does not have a cacheinfo sidecar")
      return False

    try:
      with io.open(cacheinfopath, "r", encoding="utf-8") as infile:
        cacheinfo = json.load(infile)
    except (OSError, ValueError):
      # The sidecare metadata is malformed (possibly a user tried to edit it by
      # hand)
      logger.debug("Command output has malformed cacheinfo sidecar")
      return False

    if cacheinfo.get("hash", None) != execspec["hash"]:
      # The command used to create the file has changed, so we can't use the
      # cached output.
      logger.debug("Cacheinfo has changed")
      return False

    for arg in subcommand[:]:
      if arg is self.outfile:
        # Skip the argument that we identified as the output file
        continue

      if not os.path.exists(arg):
        # If the argument is not a path to a file, then it doesn't contribute
        # to the evaluation
        continue

      if os.path.getmtime(arg) < outfile_mtime:
        # The input file is older than the output, it has not been modified
        # since this command was last executed, so move one
        continue

      if not arg.endswith(".so"):
        # The input file is not a shared object. It is either a pure object or
        # an archive (static library), and it has changed. We can't reuse the
        # cache because the meat of the output is possibly changed.
        logger.debug("Input file has changed %s", arg)
        return False

      sidecarpath = arg + ".apid"
      if not os.path.exists(sidecarpath):
        # The input file is newer than the output, and it is a shared object,
        # but we do not have an API digest sidecar file (written by this script)
        # so we must assume it's API has changed and we cannot reuse the cache.
        logger.debug(
            "Shared object has changed and there is no API digest: %s", arg)
        return False

      if os.path.getmtime(sidecarpath) < outfile_mtime:
        # The input file is newer than the output, but it is a shared object and
        # it's API has not changed since the last time we linked this output.
        # Therefore this output does not itself invalidate the cache.
        logger.debug("Input object is cache OK: %s", arg)
        continue

      # The input file is newer than the output, it is a shared object, and it's
      # API has changed since the last time we linked this output. Therefore we
      # cannot reuse the cache.
      logger.debug("Shared object API has changed: %s", arg)
      return False

    # All input files are either:
    #   a) older than the existing output file
    #   b) a shared object whose API is older than the existing output file
    # Therefore the cache is valid and we can reuse it.
    logger.debug("Using link-cache of %s", outfile)
    return True

  def write_cacheinfo(self):
    specstr = json.dumps(self.execspec, indent=2).encode("utf-8")
    with open(self.get_cacheinfopath(), "wb") as outfile:
      outfile.write(specstr)
      outfile.write(b"\n")

  def write_apid(self, linkhash_path):
    try:
      new_apid = subprocess.check_output(
          ["linkhash", self.outfile],
          executable=linkhash_path).decode("utf-8").strip()
    except subprocess.CalledProcessError:
      logger.warning("failed to linkhash")
      return

    apidpath = self.get_apidpath()
    if os.path.exists(apidpath):
      with io.open(apidpath, "r", encoding="utf-8") as infile:
        old_apid = infile.read().strip()
      if old_apid == new_apid:
        # The shared-object API has not changed. No need to update the apid
        # file.
        return
    with io.open(apidpath, "w", encoding="utf-8") as outfile:
      outfile.write(new_apid)
      outfile.write("\n")


def setup_argparser(argparser):
  argparser.add_argument(
      "--log-level", default="warning",
      choices=["debug", "info", "warning", "error"])
  argparser.add_argument("subcommand", nargs=argparse.REMAINDER)


def main():
  logging.basicConfig()
  argparser = argparse.ArgumentParser(description=__doc__)
  setup_argparser(argparser)

  try:
    import argcomplete
    argcomplete.autocomplete(argparser)
  except ImportError:
    pass

  args = argparser.parse_args()
  logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

  linkhash_path = find_linkhash()
  if linkhash_path is None:
    os.execvp(args.subcommand[0], args.subcommand)
    sys.exit(1)

  ctx = Context(args.subcommand)
  if ctx.cache_hit():
    logger.debug("Cache hit, touching %s", ctx.outfile)
    pathlib.Path(ctx.outfile).touch()
    sys.exit(0)
  else:
    logger.debug("Cache miss, executing subcommand")
    result = subprocess.call(args.subcommand)
    if ctx.outfile:
      if result == 0:
        ctx.write_cacheinfo()
        if ctx.outfile.endswith(".so"):
          ctx.write_apid(linkhash_path)
      else:
        if os.path.exists(ctx.get_cacheinfopath()):
          os.unlink(ctx.get_cacheinfopath())
        if os.path.exists(ctx.get_apidpath()):
          os.unlink(ctx.get_apidpath())
    sys.exit(result)


if __name__ == "__main__":
  main()
