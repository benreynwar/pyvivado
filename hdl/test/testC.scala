import Chisel._
import math.pow

class SimpleStream(dataWidth: Int) extends Bundle {
  val valid = Bool(INPUT)
  val data = Bits(INPUT, width = dataWidth)
}

class TestC(dataWidth: Int) extends Module {
  val io = new Bundle {
    val i = new SimpleStream(dataWidth).asInput
    val o = new SimpleStream(dataWidth).asOutput
  }
  io.o := io.i
}

