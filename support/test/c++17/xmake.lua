target("c++17/filesystem")
  enable_if_cxx_header("filesystem")
  set_languages("c++17")
  add_files("filesystem.cc")
  add_tests("default", {
    pass_outputs =
      "test__filesystem__‘dir_copy’\n" ..
      "test__filesystem__‘dir_copy’/‘file_copy’.txt\n" ..
      "test__filesystem__‘dir_copy’/‘file’.txt\n" ..
      "test__filesystem__‘dir’\n" ..
      "test__filesystem__‘dir’/‘file_copy’.txt\n" ..
      "test__filesystem__‘dir’/‘file’.txt\n"})

target("c++17/fstream")
  enable_if_cxx_header("filesystem")
  set_languages("c++17")
  add_files("fstream.cc")
  add_tests("default", {pass_outputs = "Hello, world!\n"})
