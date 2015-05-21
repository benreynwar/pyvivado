scalaVersion := "2.10.4"

libraryDependencies += "edu.berkeley.cs" %% "chisel" % "latest.release"

scalaSource in Compile <<= baseDirectory(_ / "hdl")