library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.axi_utils.all;

entity axi_adder is
  --- Address 0: read/write to intA
  --- Address 1: read/write to intB
  --- Address 2: read only to intC
  --- Address 3: read only (Whether we've had an error)
  --- intC = intA + intB
  --- We assume that awvalid and wvalid are applied simulataneously.
  port (
    clk: in std_logic;
    reset: in std_logic;
    i: in axi4lite_m2s;
    o: out axi4lite_s2m
    );
end axi_adder;

architecture arch of axi_adder is
  signal intA: unsigned(15 downto 0);
  signal intB: unsigned(15 downto 0);
  signal intC: unsigned(16 downto 0);
  -- Checking our assumption that awvalid and wvalid are
  -- always applied together.
  signal had_error: std_logic;
begin

  intC <= resize(intA, 17) + resize(intB, 17);
    
  process(clk)
  begin
    if rising_edge(clk) then
      o <= DEFAULT_AXI4LITE_S2M;
      if reset = '1' then
        intA <= (others => '0');
        intB <= (others => '0');
        had_error <= '0';
      else
        -- Handle writing of registers.
        if (i.awvalid = '1') then
          --- We assume that awvalid and wvalid are applied simulataneously.
          if (i.wvalid = '0') then
            had_error <= '1';
          end if;
          o.bvalid <= '1';
          if (unsigned(i.awaddr) = 0) then
            intA <= unsigned(i.wdata(15 downto 0));
          elsif (unsigned(i.awaddr) = 1) then
            intB <= unsigned(i.wdata(15 downto 0));
          else
            -- Invalid write address.
            o.bresp <= axi_resp_DECERR;
          end if;
        end if;
        -- Handle reading of registers.
        if (i.arvalid = '1') then
          o.rvalid <= '1';
          if (unsigned(i.araddr) = 0) then
            o.rdata(15 downto 0) <= std_logic_vector(intA);
          elsif (unsigned(i.araddr) = 1) then
            o.rdata(15 downto 0) <= std_logic_vector(intB);
          elsif (unsigned(i.araddr) = 2) then
            o.rdata(16 downto 0) <= std_logic_vector(intC);
          elsif (unsigned(i.araddr) = 3) then
            o.rdata(0) <= had_error;
          else
            -- Invalid read address.
            o.rresp <= axi_resp_DECERR;
          end if;
        end if;
      end if;
    end if;
  end process;
  
end arch;
