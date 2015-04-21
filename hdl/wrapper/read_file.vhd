-- -*- vhdl -*- 

library ieee;
use ieee.std_logic_1164.all;

library std;
use std.textio;
use work.txt_util.all;

entity ReadFile is
  generic (FILENAME: string;
           WIDTH: positive);
  port (clk: in std_logic;
        out_data: out std_logic_vector(0 to WIDTH-1));
end ReadFile;

architecture arch of ReadFile is
  file input_file : textio.text;
  signal the_out_data: std_logic_vector(0 to WIDTH-1) := (others => '0');
begin
  out_data <= the_out_data;
  process
    variable input_line : textio.line;
    variable input_string : string(1 to WIDTH); 
  begin

    textio.file_open(input_file, FILENAME, read_mode);

    while not textio.endfile(input_file) loop
      textio.readline(input_file, input_line);
      textio.read(input_line, input_string);
      the_out_data <= to_std_logic_vector(input_string);

      wait until rising_edge(clk);

    end loop;

    textio.file_close(input_file);

    wait;
  end process;

end arch;
