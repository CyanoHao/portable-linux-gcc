target("c++11/thread")
  set_languages("c++11")
  add_files("thread.cc")
  add_syslinks("pthread")
  add_tests("default", {
    pass_outputs =
      "l = 1000000\n" ..
      "l = 1000000\n" ..
      "l = 1000000\n" ..
      "l = 1000000\n" ..
      "l = 1000000\n" ..
      "l = 1000000\n" ..
      "l = 1000000\n" ..
      "l = 1000000\n" ..
      "l = 1000000\n" ..
      "l = 1000000\n" ..
      "g = 10000000\n"})
