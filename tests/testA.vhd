library ieee;
use ieee.std_logic_1164.all;

use work.testA_definitions.all;

entity TestA is
  generic (
    DATA_WIDTH: positive;
    ARRAY_LENGTH: positive
    );
  port (
    i_valid: in std_logic;
    i_data: in std_logic_vector(DATA_WIDTH-1 downto 0);
    i_array: in array_of_t_data(ARRAY_LENGTH-1 downto 0);
    o_valid: out std_logic;
    o_data: out std_logic_vector(DATA_WIDTH-1 downto 0);
    o_array: out array_of_t_data(ARRAY_LENGTH-1 downto 0)
    );
end TestA;

architecture arch of TestA is
begin
  o_valid <= i_valid;
  o_data <= i_data;
  o_array <= i_array;
end arch;
