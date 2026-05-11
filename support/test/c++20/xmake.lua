target("c++20/source_location")
  set_languages("c++20")
  add_files("‘source_location’.cc")
  add_tests("default", {pass_outputs = ".*‘source_location’%.cc\n"})
