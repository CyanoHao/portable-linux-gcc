add_rules("mode.debug", "mode.release")
set_policy("build.c++.modules.gcc.cxx11abi", true)

includes("enable_if.lua")

includes("c89/xmake.lua")
includes("c23/xmake.lua")

includes("c++98/xmake.lua")
includes("c++11/xmake.lua")
includes("c++17/xmake.lua")
includes("c++20/xmake.lua")
includes("c++23/xmake.lua")

includes("gnu++98/xmake.lua")

includes("lto/xmake.lua")
includes("openmp/xmake.lua")
