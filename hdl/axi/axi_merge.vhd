-- -*- vhdl -*- 

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.axi_utils.all;
use work.pyvivado_utils.all;

entity axi_merge is
  -- Assumes that when writing awvalid and wvalid are asserted at the same time.
  -- Assumes reading and writing do not happen at same time.
  -- Assumes master is always ready for response.
  generic (
    N_MASTERS: positive
    );
  port (
    clk: in std_logic;
    reset: in std_logic;
    i_m: in array_of_axi4lite_m2s(N_MASTERS-1 downto 0);
    o_m: out array_of_axi4lite_s2m(N_MASTERS-1 downto 0);
    o_s: out axi4lite_m2s;
    i_s: in axi4lite_s2m
    );
end axi_merge;

architecture arch of axi_merge is
  signal m_master_index: integer range 0 to N_MASTERS-1;
  signal waiting: std_logic;
  signal m_read_waiting: std_logic;
  signal m_write_waiting: std_logic;
begin

  waiting <= m_read_waiting or m_write_waiting;

  o_ms: for mi in 0 to N_MASTERS-1 generate
    o_m(mi).awready <= '1' when mi = m_master_index and waiting = '0' else
                       '0';
    o_m(mi).arready <= '1' when mi = m_master_index and waiting = '0' else
                       '0';
    o_m(mi).wready <= '1' when mi = m_master_index and waiting = '0' else
                      '0';
    o_m(mi).bvalid <= i_s.bvalid when mi = m_master_index and waiting = '1' else
                      '0';
    o_m(mi).bresp <= i_s.bresp;
    o_m(mi).rvalid <= i_s.rvalid when mi = m_master_index and waiting = '1' else
                      '0';
    o_m(mi).rdata <= i_s.rdata;
    o_m(mi).rresp <= i_s.rresp;
  end generate;
  
  o_s.awvalid <= i_m(m_master_index).awvalid when waiting = '0' else
                 '0';
  o_s.awaddr <= i_m(m_master_index).awaddr;
  o_s.wvalid <= i_m(m_master_index).wvalid when waiting = '0' else
                '0';
  o_s.wdata <= i_m(m_master_index).wdata;
  o_s.arvalid <= i_m(m_master_index).arvalid when waiting = '0' else
                 '0';
  o_s.araddr <= i_m(m_master_index).araddr;
  o_s.bready <= m_write_waiting;
  o_s.rready <= m_read_waiting;
  
  process(clk)
  begin
    if rising_edge(clk) then
      if reset = '1' then
        m_master_index <= 0;
        m_read_waiting <= '0';
        m_write_waiting <= '0';
      else
        if waiting = '0' then
          if (i_m(m_master_index).awvalid = '1') then
            m_write_waiting <= '1';
          end if;
          if (i_m(m_master_index).arvalid = '1') then
            m_read_waiting <= '1';
          end if;
          if (i_m(m_master_index).arvalid = '0') and (i_m(m_master_index).awvalid = '0') then
            if m_master_index = N_MASTERS-1 then
              m_master_index <= 0;
            else
              m_master_index <= m_master_index + 1;
            end if;
          end if;
        else
          if (i_s.bvalid = '1') then
            m_write_waiting <= '0';
          end if;
          if (i_s.rvalid = '1') then
            m_read_waiting <= '0';
          end if;
        end if;
      end if;
    end if;
  end process;
  
end arch;
