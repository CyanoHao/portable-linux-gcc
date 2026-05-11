target("gnu++98/bits-stdc++")
  add_files("bits-stdc++.cc")
  add_tests("default", {pass_outputs = "Hello, world!\n"})
