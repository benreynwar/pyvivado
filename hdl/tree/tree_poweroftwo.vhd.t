-- -*- vhdl -*-

library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.pyvivado_utils.all;

entity tree_poweroftwo_{{tree_name}} is
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
end tree_poweroftwo_{{tree_name}};


architecture arch of tree_poweroftwo_{{tree_name}} is
  signal intermed_data: std_logic_vector(N_INPUTS/2*WIDTH-1 downto 0);
  constant INTERMED_ADDRESS_WIDTH: positive := INPUT_ADDRESS_WIDTH+1;
  signal intermed_addresses: std_logic_vector(N_INPUTS/2*INTERMED_ADDRESS_WIDTH-1 downto 0);

begin

  more_than_two: if N_INPUTS > 2 generate
    
    make_twos_layer: for ii in 0 to N_INPUTS/2-1 generate
      twoer: entity work.tree_binary_leaf_{{tree_name}}
        generic map (
          WIDTH => WIDTH,
          INPUT_ADDRESS_WIDTH => INPUT_ADDRESS_WIDTH
          )
        port map (
          i_data => i_data((ii+1)*2*WIDTH-1 downto ii*2*WIDTH),
          i_addresses => i_addresses((ii+1)*2*INPUT_ADDRESS_WIDTH-1 downto 
                                     ii*2*INPUT_ADDRESS_WIDTH),
          o_data => intermed_data((ii+1)*WIDTH-1 downto ii*WIDTH),
          o_address => intermed_addresses((ii+1)*INTERMED_ADDRESS_WIDTH-1 downto
                                          ii*INTERMED_ADDRESS_WIDTH)
          );
    end generate;
    
    zero: entity work.tree_poweroftwo_{{tree_name}}
      generic map (
        WIDTH => WIDTH,
        N_INPUTS => N_INPUTS/2,
        INPUT_ADDRESS_WIDTH => INPUT_ADDRESS_WIDTH+1
        )
      port map (
        i_data => intermed_data,
        i_addresses => intermed_addresses,
        o_data => o_data,
        o_address => o_address
        );

  end generate;
  
  down_to_two: if N_INPUTS = 2 generate
    down_to_two_inst: entity work.tree_binary_leaf_{{tree_name}}
      generic map (
        WIDTH => WIDTH,
        INPUT_ADDRESS_WIDTH => INPUT_ADDRESS_WIDTH
        )
      port map (
        i_data => i_data,
        i_addresses => i_addresses,
        o_data => o_data,
        o_address => o_address
        );
  end generate;
      
  
end arch;
