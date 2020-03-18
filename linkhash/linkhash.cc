// Copyright 2020 Josh Bialkowski <josh.bialkowski@gmail.com>
#include <fcntl.h>
#include <linux/elf.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <cstring>
#include <string>
#include <vector>

#include <fmt/format.h>
#include <loki/ScopeGuard.h>
#include <openssl/sha.h>

#include "argue/argue.h"
#include "tangent/util/elf_file.h"
#include "tangent/util/stdio_filebuf.h"

#define LINKHASH_VERSION \
  { 0, 1, 0, "dev", 1 }

template <class Traits>
std::vector<std::string> get_api_from_section(ElfFile<Traits> elf_file,
                                              typename Traits::Shdr* shdr) {
  typename Traits::Shdr* string_scn = elf_file.get_section(shdr->sh_link);
  char* string_data = elf_file.get_section_data(string_scn->sh_offset);

  std::vector<std::string> output{};
  char* section_data = elf_file.get_section_data(shdr->sh_offset);
  for (char* sym_ptr = section_data; sym_ptr < &section_data[shdr->sh_size];
       sym_ptr += shdr->sh_entsize) {
    typename Traits::Sym* sym =
        reinterpret_cast<typename Traits::Sym*>(sym_ptr);
    std::string bindstr{};
    switch (Traits::st_bind(sym->st_info)) {
      case STB_GLOBAL:
        bindstr = "GLOBAL";
        break;
      case STB_WEAK:
        bindstr = "WEAK";
        break;
      default:
        continue;
    }
    const char* name = &string_data[sym->st_name];
    output.push_back(bindstr + "," + std::string(name));
  }
  return output;
}

template <class Traits>
std::vector<std::string> get_api_from_image(char* image) {
  ElfFile<Traits> elf_file{image};

  if (elf_file.get_header()->e_type != ET_DYN) {
    throw std::runtime_error(
        fmt::format("Input file is not a shared object ({}), e_type={}", ET_DYN,
                    elf_file.get_header()->e_type));
  }

  for (auto& shdr : elf_file.iter_shdr()) {
    switch (shdr.sh_type) {
      case SHT_SYMTAB:
      case SHT_DYNSYM:
        return get_api_from_section(elf_file, &shdr);
      default:
        continue;
    }
  }

  throw std::runtime_error("Shared object contains no symbol table section");
}

std::vector<std::string> get_api(const std::string filepath) {
  int fd = open(filepath.c_str(), O_RDONLY);
  if (fd == -1) {
    throw std::runtime_error(fmt::format("Failed to open {} for reading: {}",
                                         filepath, strerror(errno)));
  }
  Loki::ScopeGuard _close = Loki::MakeGuard(close, fd);

  struct stat statbuf {};
  int err = fstat(fd, &statbuf);
  if (err) {
    throw std::runtime_error(
        fmt::format("Failed to stat {} for size", filepath));
  }

  void* mem =
      mmap(nullptr, statbuf.st_size, PROT_READ, MAP_SHARED, fd, /*offset=*/0);
  if (!mem) {
    throw std::runtime_error(fmt::format("Can't map the file {}", filepath));
  }
  Loki::ScopeGuard _unmap = Loki::MakeGuard(munmap, mem, statbuf.st_size);

  char* image = static_cast<char*>(mem);
  if (std::memcmp(image, ELFMAG, 4) != 0) {
    throw std::runtime_error(fmt::format("File {} has wrong magic", filepath));
  }

  ElfClass elf_class = static_cast<ElfClass>(image[EI_CLASS]);
  switch (elf_class) {
    case ELF32:
      return get_api_from_image<Traits32>(image);
    case ELF64:
      return get_api_from_image<Traits64>(image);
    default:
      throw std::runtime_error(
          fmt::format("Unexpected elf_class: {}", elf_class));
  }
}

struct ProgramOptions {
  std::string infilepath;
  std::string outfilepath;
  bool dump_api;
};

int main(int argc, char** argv) {
  argue::Parser::Metadata meta{};
  meta.add_help = true;
  meta.name = "linkhash";
  meta.version = argue::VersionString LINKHASH_VERSION;
  meta.author = "Josh Bialkowski <josh.bialkowsk@gmail.com>";
  meta.prolog = R"prolog(
linkhash computes a sha1sum of the "API" of a shared object (i.e. the list
of externally visable symbols).
)prolog";

  argue::Parser parser{meta};
  ProgramOptions progopts{};

  using argue::keywords::action;
  using argue::keywords::default_;
  using argue::keywords::dest;
  using argue::keywords::help;
  // clang-format off
  parser.add_argument(
    "-o", "--outfile", dest=&progopts.outfilepath, default_=std::string("-"),
    help="Path to the file to write. '-' means write to stdout (default)");
  parser.add_argument(
    "filepath", dest=&progopts.infilepath);
  parser.add_argument(
    "--dump-api", action="store_true", dest=&progopts.dump_api,
    help="If specified, then write out the API specification rather than"
         " it's hash");
  // clang-format on

  int parse_result = parser.parse_args(argc, argv);
  switch (parse_result) {
    case argue::PARSE_ABORTED:
      return 0;
    case argue::PARSE_EXCEPTION:
      return 1;
    case argue::PARSE_FINISHED:
      break;
  }

  std::vector<std::string> api;
  try {
    api = get_api(progopts.infilepath);
  } catch (const std::runtime_error& err) {
    std::cerr << err.what() << "\n";
    exit(1);
  }

  std::sort(api.begin(), api.end());

  int outfd{0};
  if (progopts.outfilepath == "-") {
    outfd = dup(STDOUT_FILENO);
  } else {
    outfd = open(progopts.outfilepath.c_str(), O_WRONLY | O_CREAT, 0655);
  }

  __gnu_cxx::stdio_filebuf<char> filebuf{outfd, std::ios::out};
  std::ostream outstream{&filebuf};

  if (progopts.dump_api) {
    for (std::string& entry : api) {
      outstream << entry << "\n";
    }
    outstream.flush();
    exit(0);
  }

  SHA_CTX sha_ctx{};
  SHA1_Init(&sha_ctx);
  for (std::string& entry : api) {
    SHA1_Update(&sha_ctx, &entry[0], entry.size());
    SHA1_Update(&sha_ctx, "\n", 1);
  }

  unsigned char digest[SHA_DIGEST_LENGTH];
  SHA1_Final(digest, &sha_ctx);

  for (size_t idx = 0; idx < SHA_DIGEST_LENGTH; idx++) {
    outstream << std::hex << static_cast<int>(digest[idx]);
  }
  outstream << "\n";
  outstream.flush();
  exit(0);
}
