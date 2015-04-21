-- -*- vhdl -*- 

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.axi_utils.all;
use work.pyvivado_utils.all;

entity axi_fail is
  -- Always returns a DECERROR
  port (
    clk: in std_logic;
    reset: in std_logic;
    i: in axi4lite_m2s;
    o: out axi4lite_s2m
    );
end axi_fail;

architecture arch of axi_fail is
begin

  process(clk)
  begin
    if rising_edge(clk) then
      o <= DEFAULT_AXI4LITE_S2M;
      o.bresp <= axi_resp_DECERR;
      o.rresp <= axi_resp_DECERR;
      if reset = '0' then
        if (i.awvalid = '1') then
          o.bvalid <= '1';
        end if;
        if (i.arvalid = '1') then
          o.rvalid <= '1';
        end if;
      end if;
    end if;
  end process;
  
end arch;
