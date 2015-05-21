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

class TestCTests(c: TestC, dataWidth: Int) extends Tester(c) {
  val maxData = pow(2, dataWidth).toInt
  for (t <- 0 until 16) {
    val i_valid = rnd.nextInt(2)
    val i_data = rnd.nextInt(maxData)
    poke(c.io.i.valid, i_valid)
    poke(c.io.i.data, i_data)
    expect(c.io.o.valid, i_valid)
    expect(c.io.o.data, i_data)
    step(1)
  }
}

