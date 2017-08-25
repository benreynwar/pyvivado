-- -*- vhdl -*- 

library ieee;
use ieee.std_logic_1164.all;

use work.axi_utils.all;

entity {{dut_name}}_jtag is
  port (
    clk_in_n: in std_logic;
    clk_in_p: in std_logic;
    reset: in std_logic
    );
end entity;

architecture arch of {{dut_name}}_jtag is
  -- Basic clk and reset signals
  signal resetn: std_logic;
  signal clk: std_logic;
  -- Axi signals
  signal m2s: axi4lite_m2s;
  signal s2m: axi4lite_s2m;

  component clk_wiz_0 port (
    clk_in1_n: in std_logic;
    clk_in1_p: in std_logic;
    reset: in std_logic;
    clk_out1: out std_logic
    );
  end component;

  component jtag_axi_0 port (
    aclk: in std_logic;
    aresetn: in std_logic;
    m_axi_araddr: out std_logic_vector(31 downto 0); 
    m_axi_arprot: out std_logic_vector(2 downto 0); 
    m_axi_arready: in std_logic;
    m_axi_arvalid: out std_logic;
    m_axi_awaddr: out std_logic_vector(31 downto 0); 
    m_axi_awprot: out std_logic_vector(2 downto 0); 
    m_axi_awready: in std_logic; 
    m_axi_awvalid: out std_logic; 
    m_axi_bready: out std_logic; 
    m_axi_bresp: in std_logic_vector(1 downto 0); 
    m_axi_bvalid: in std_logic; 
    m_axi_rdata: in std_logic_vector(31 downto 0);
    m_axi_rready: out std_logic;
    m_axi_rresp: in std_logic_vector(1 downto 0);
    m_axi_rvalid: in std_logic;
    m_axi_wdata: out std_logic_vector(31 downto 0); 
    m_axi_wready: in std_logic;
    m_axi_wstrb: out std_logic_vector(3 downto 0); 
    m_axi_wvalid: out std_logic
    );
   end component;

begin

   resetn <= not reset;
   
  the_clock_wizard: clk_wiz_0
    port map(
      clk_in1_n => clk_in_n,
      clk_in1_p => clk_in_p,
      reset => reset,
      clk_out1 => clk
      );

  jtag_to_axi_master: jtag_axi_0
    port map(
      aclk => clk,
      aresetn => resetn,
      m_axi_araddr => m2s.araddr,
      m_axi_arprot => m2s.arprot,
      m_axi_arready => s2m.arready,
      m_axi_arvalid => m2s.arvalid,
      m_axi_awaddr => m2s.awaddr,
      m_axi_awprot => m2s.awprot,
      m_axi_awready => s2m.awready,
      m_axi_awvalid => m2s.awvalid,
      m_axi_bready => m2s.bready,
      m_axi_bresp => s2m.bresp,
      m_axi_bvalid => s2m.bvalid,
      m_axi_rdata => s2m.rdata,
      m_axi_rready => m2s.rready,
      m_axi_rresp => s2m.rresp,
      m_axi_rvalid => s2m.rvalid,
      m_axi_wdata => m2s.wdata,
      m_axi_wready => s2m.wready,
      m_axi_wstrb => m2s.wstrb,
      m_axi_wvalid => m2s.wvalid
      );

  axi_wrapped_dut: entity work.{{dut_name}}
    {% if dut_parameters %}
    generic map(
      {% for name, value in dut_parameters.items() %}
      {{name}} => {{value}} {% if not loop.last %},{% endif %}
      {% endfor %}
      )
    {% endif %}
    port map (
      clk => clk,
      reset => reset,
      m2s => m2s,
      s2m => s2m
      );
  
end arch;
