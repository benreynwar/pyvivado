-- -*- vhdl -*-

library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tree_binary_leaf_maximum is
  generic (
    WIDTH: integer;
    INPUT_ADDRESS_WIDTH: integer := 0
    );
  port (
    i_data: in std_logic_vector(2*WIDTH-1 downto 0);
    i_addresses: in std_logic_vector(2*INPUT_ADDRESS_WIDTH-1 downto 0);
    o_data: out std_logic_vector(WIDTH-1 downto 0);
    o_address: out std_logic_vector(INPUT_ADDRESS_WIDTH+1-1 downto 0)
    );
end tree_binary_leaf_maximum;


architecture arch of tree_binary_leaf_maximum is
  signal i_data0: unsigned(WIDTH-1 downto 0);
  signal i_data1: unsigned(WIDTH-1 downto 0);
  signal i_address0: std_logic_vector(INPUT_ADDRESS_WIDTH-1 downto 0);
  signal i_address1: std_logic_vector(INPUT_ADDRESS_WIDTH-1 downto 0);
  signal first_bigger: std_logic;
begin
  i_data0 <= unsigned(i_data(WIDTH-1 downto 0));
  i_data1 <= unsigned(i_data(2*WIDTH-1 downto WIDTH));
  i_address0 <= i_addresses(INPUT_ADDRESS_WIDTH-1 downto 0);
  i_address1 <= i_addresses(2*INPUT_ADDRESS_WIDTH-1 downto INPUT_ADDRESS_WIDTH);
  
  first_bigger <= '0' when i_data0 < i_data1 else
                  '1';
  o_data <= std_logic_vector(i_data0) when first_bigger = '1' else
            std_logic_vector(i_data1);
  o_address <= '0' & i_address0 when first_bigger = '1' else
               '1' & i_address1;
  
end arch;
