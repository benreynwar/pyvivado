-- -*- vhdl -*-

library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.pyvivado_utils.all;

entity tree_notpoweroftwo_{{tree_name}} is
  generic (
    WIDTH: integer;
    N_INPUTS: integer;
    INPUT_ADDRESS_WIDTH: integer := 0
    );
  port (
    i_data: in std_logic_vector(N_INPUTS*WIDTH-1 downto 0);
    i_addresses: in std_logic_vector(N_INPUTS*INPUT_ADDRESS_WIDTH-1 downto 0);
    o_data: out std_logic_vector(WIDTH-1 downto 0);
    o_address: out std_logic_vector(
      INPUT_ADDRESS_WIDTH+logceil(N_INPUTS)-1 downto 0)
    );
end tree_notpoweroftwo_{{tree_name}};


architecture arch of tree_notpoweroftwo_{{tree_name}} is
  constant ZEROS: positive := 2 ** (logceil(N_INPUTS+1)-1);
  constant NONZEROS: positive := N_INPUTS - ZEROS;
  constant INTERMED_ADDRESS_WIDTH: positive :=
    INPUT_ADDRESS_WIDTH + logceil(ZEROS);
  signal zero_i_data: std_logic_vector(ZEROS*WIDTH-1 downto 0);
  signal zero_i_addresses: std_logic_vector(
    ZEROS*INPUT_ADDRESS_WIDTH-1 downto 0);
  signal nonzero_i_data: std_logic_vector(NONZEROS*WIDTH-1 downto 0);
  signal nonzero_i_addresses: std_logic_vector(
    NONZEROS*INPUT_ADDRESS_WIDTH-1 downto 0);
  signal zero_o_data: std_logic_vector(WIDTH-1 downto 0);
  signal zero_o_address: std_logic_vector(
    INTERMED_ADDRESS_WIDTH-1 downto 0);
  signal nonzero_o_data: std_logic_vector(WIDTH-1 downto 0);
  signal nonzero_o_address: std_logic_vector(
    INPUT_ADDRESS_WIDTH+logceil(NONZEROS)-1 downto 0);
  signal padded_nonzero_o_address: std_logic_vector(
    INTERMED_ADDRESS_WIDTH-1 downto 0);
  signal two_i_data: std_logic_vector(2*WIDTH-1 downto 0);
  signal two_i_addresses: std_logic_vector(
    2*(INPUT_ADDRESS_WIDTH+logceil(ZEROS))-1 downto 0);
    
   component tree_generic_{{tree_name}} is
     generic (
        WIDTH: integer;
        N_INPUTS: integer;
        INPUT_ADDRESS_WIDTH: integer := 0
        );
      port (
        i_data: in std_logic_vector(N_INPUTS*WIDTH-1 downto 0);
        i_addresses: in std_logic_vector(N_INPUTS*INPUT_ADDRESS_WIDTH-1 downto 0);
        o_data: out std_logic_vector(WIDTH-1 downto 0);
        o_address: out std_logic_vector(INPUT_ADDRESS_WIDTH+logceil(N_INPUTS)-1 downto 0)
        );
    end component;
        
begin

  zero_i_data <= i_data(ZEROS*WIDTH-1 downto 0);
  nonzero_i_data <= i_data(N_INPUTS*WIDTH-1 downto ZEROS*WIDTH);
  zero_i_addresses <= i_addresses(ZEROS*INPUT_ADDRESS_WIDTH-1 downto 0);
  nonzero_i_addresses <= i_addresses(N_INPUTS*INPUT_ADDRESS_WIDTH-1 downto
                                     ZEROS*INPUT_ADDRESS_WIDTH);
  process(nonzero_o_address)
  begin
    padded_nonzero_o_address <= (others => '0');
    padded_nonzero_o_address(
      INPUT_ADDRESS_WIDTH+logceil(NONZEROS)-1 downto 0) <= nonzero_o_address;
  end process;
  
  zero: entity work.tree_poweroftwo_{{tree_name}}
    generic map(
      N_INPUTS => ZEROS,
      WIDTH => WIDTH,
      INPUT_ADDRESS_WIDTH => INPUT_ADDRESS_WIDTH
      )
    port map(
      i_data => zero_i_data,
      i_addresses => zero_i_addresses,
      o_data => zero_o_data,
      o_address => zero_o_address
      );

  general: tree_generic_{{tree_name}}
    generic map(
      N_INPUTS => NONZEROS,
      WIDTH => WIDTH,
      INPUT_ADDRESS_WIDTH => INPUT_ADDRESS_WIDTH
      )
    port map(
      i_data => nonzero_i_data,
      i_addresses => nonzero_i_addresses,
      o_data => nonzero_o_data,
      o_address => nonzero_o_address
      );

  two_i_data(WIDTH-1 downto 0) <= zero_o_data;
  two_i_data(2*WIDTH-1 downto WIDTH) <= nonzero_o_data;
  two_i_addresses(INTERMED_ADDRESS_WIDTH-1 downto 0) <= zero_o_address;
  two_i_addresses(2*INTERMED_ADDRESS_WIDTH-1 downto INTERMED_ADDRESS_WIDTH) <=
    padded_nonzero_o_address;
  
  combine_two: entity work.tree_binary_leaf_{{tree_name}}
    generic map(
      WIDTH => WIDTH,
      INPUT_ADDRESS_WIDTH => INPUT_ADDRESS_WIDTH + logceil(ZEROS)
      )
    port map(
      i_data => two_i_data,
      i_addresses => two_i_addresses,
      o_data => o_data,
      o_address => o_address
      );
  
end arch;
