import Chisel._

object Generator {

  case class ParseException(message: String) extends Exception(message)

  def main(args: Array[String]): Unit = {
    if (args.length < 2) {
      throw ParseException("Required moduleName and outputDirectory arguements.")
    } else {
      val moduleName = args(0)
      val outputDirectory = args(1)
      val tutArgs = args.slice(2, args.length) 
      moduleName match {
	case "TestC" => testC(tutArgs, outputDirectory)
	case _ => throw ParseException("Unknown module.")
      }
    }
  }

  def testC(args: Array[String], outputDirectory: String): Unit = {
    var i = 0
    var dataWidth = 0
    var dataWidthSet = false
    while (i < args.length) {
      val arg = args(i)
      arg match {
        case "--dataWidth" => dataWidth = args(i+1).toInt; i+=1; dataWidthSet = true
	case _ => throw ParseException(s"Unrecognized parameter: $arg.")
      }
      i += 1
    }
    if (!dataWidthSet) {
      throw ParseException("dataWidth must be specified.")
    } else {
      val testArgs = Array("--backend", "v", "--targetDir", outputDirectory)
      chiselMainTest(testArgs, () => Module(
	new TestC(dataWidth=dataWidth))){
  	  c => new TestCTests(c, dataWidth=dataWidth)
	}
    }
  }
}
