-- -*- vhdl -*- 

library ieee;
use ieee.std_logic_1164.all;

use work.axi_utils.all;

entity JtagAxiWrapperNoReset is
  port (
    clk_in_p: in std_logic;
    clk_in_n: in std_logic
    );
end JtagAxiWrapperNoReset;

architecture arch of JtagAxiWrapperNoReset is
  constant reset: std_logic := '0';
begin
  inner_jtag_axi: entity work.JtagAxiWrapper
    port map(
      clk_in_p => clk_in_p,
      clk_in_n => clk_in_n,
      reset => reset
      );
end arch;
