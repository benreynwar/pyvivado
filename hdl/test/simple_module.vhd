library ieee;
use ieee.std_logic_1164.all;

-- Define a simple module through which the wires pass
-- straight through.
entity SimpleModule is
  generic (
    DATA_WIDTH: positive
    );
  port (
    i_valid: in std_logic;
    i_data: in std_logic_vector(DATA_WIDTH-1 downto 0);
    o_valid: out std_logic;
    o_data: out std_logic_vector(DATA_WIDTH-1 downto 0)
    );
end SimpleModule;

architecture arch of SimpleModule is
begin
  o_valid <= i_valid;
  o_data <= i_data;
end arch;
