-- -*- vhdl -*- 
  
library ieee;
use ieee.std_logic_1164.all;

entity FileTestBenchWrapped is
end FileTestBenchWrapped;
 
architecture arch of FileTestBenchWrapped is
  constant DATAINFILENAME: string := "{{input_filename}}";
  constant DATAOUTFILENAME: string := "{{output_filename}}";
begin

  ftb: entity work.FileTestBench
    generic map(
      DATAINFILENAME => DATAINFILENAME,
      DATAOUTFILENAME => DATAOUTFILENAME
    );
end arch;
