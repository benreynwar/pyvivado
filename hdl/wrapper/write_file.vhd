-- -*- vhdl -*- 

library ieee;
use ieee.std_logic_1164.all;

library std;
use std.textio;
use work.txt_util.all;

entity WriteFile is
  generic (FILENAME: string;
           WIDTH: positive);
  port (clk: in std_logic;
        in_data: in std_logic_vector(0 to WIDTH-1));
end WriteFile;

architecture arch of WriteFile is
  file output_file : textio.text;
begin
  process
    variable output_line : textio.line;
  begin

    textio.file_open(output_file, FILENAME, write_mode);

    while true loop
      print(output_file, str(in_data)); 
      wait until rising_edge(clk);
    end loop;

    textio.file_close(output_file);

    wait;
  end process;

end arch;
