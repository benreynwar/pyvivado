-- -*- vhdl -*- 

library ieee;
use ieee.std_logic_1164.all;

use work.axi_utils.all;

entity {{dut_name}}_jtag is
  port (
    clk_in_n: in std_logic;
    clk_in_p: in std_logic
    );
end entity;

architecture arch of {{dut_name}}_jtag is
  -- Basic clk signals
  signal clk: std_logic;
  signal jtagtoaxi_clk: std_logic;
  -- Axi signals
  signal m2s: axi4lite_m2s;
  signal s2m: axi4lite_s2m;
  signal jtagtoaxim2s: axi4lite_m2s;
  signal jtagtoaxis2m: axi4lite_s2m;

  component clk_wiz_0 port (
    clk_in1_n: in std_logic;
    clk_in1_p: in std_logic;
    reset: in std_logic;
    clk_out1: out std_logic;
    clk_out2: out std_logic
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

  component axi_clock_converter_0 port (
    s_axi_aclk: in std_logic;
    s_axi_aresetn: in std_logic;
    s_axi_araddr: in std_logic_vector(31 downto 0);
    s_axi_arprot: in std_logic_vector(2 downto 0);
    s_axi_arready: out std_logic;
    s_axi_arvalid: in std_logic;
    s_axi_awaddr: in std_logic_vector(31 downto 0);
    s_axi_awprot: in std_logic_vector(2 downto 0);
    s_axi_awready: out std_logic;
    s_axi_awvalid: in std_logic;
    s_axi_bready: in std_logic;
    s_axi_bresp: out std_logic_vector(1 downto 0);
    s_axi_bvalid: out std_logic;
    s_axi_rdata: out std_logic_vector(31 downto 0);
    s_axi_rready: in std_logic;
    s_axi_rresp: out std_logic_vector(1 downto 0);
    s_axi_rvalid: out std_logic;
    s_axi_wdata: in std_logic_vector(31 downto 0);
    s_axi_wready: out std_logic;
    s_axi_wstrb: in std_logic_vector(3 downto 0);
    s_axi_wvalid: in std_logic;
    m_axi_aclk: in std_logic;
    m_axi_aresetn: in std_logic;
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

  the_clock_wizard: clk_wiz_0
    port map(
      clk_in1_n => clk_in_n,
      clk_in1_p => clk_in_p,
      reset => '0',
      clk_out1 => jtagtoaxi_clk,
      clk_out2 => clk
      );

  jtag_to_axi_master: jtag_axi_0
    port map(
      aclk => jtagtoaxi_clk,
      aresetn => '1',
      m_axi_araddr => jtagtoaxim2s.araddr,
      m_axi_arprot => jtagtoaxim2s.arprot,
      m_axi_arready => jtagtoaxis2m.arready,
      m_axi_arvalid => jtagtoaxim2s.arvalid,
      m_axi_awaddr => jtagtoaxim2s.awaddr,
      m_axi_awprot => jtagtoaxim2s.awprot,
      m_axi_awready => jtagtoaxis2m.awready,
      m_axi_awvalid => jtagtoaxim2s.awvalid,
      m_axi_bready => jtagtoaxim2s.bready,
      m_axi_bresp => jtagtoaxis2m.bresp,
      m_axi_bvalid => jtagtoaxis2m.bvalid,
      m_axi_rdata => jtagtoaxis2m.rdata,
      m_axi_rready => jtagtoaxim2s.rready,
      m_axi_rresp => jtagtoaxis2m.rresp,
      m_axi_rvalid => jtagtoaxis2m.rvalid,
      m_axi_wdata => jtagtoaxim2s.wdata,
      m_axi_wready => jtagtoaxis2m.wready,
      m_axi_wstrb => jtagtoaxim2s.wstrb,
      m_axi_wvalid => jtagtoaxim2s.wvalid
      );

  clock_domain_crossing: axi_clock_converter_0
    port map (
      s_axi_aclk => jtagtoaxi_clk,
      s_axi_aresetn => '1',
      s_axi_araddr => jtagtoaxim2s.araddr,
      s_axi_arprot => jtagtoaxim2s.arprot,
      s_axi_arready => jtagtoaxis2m.arready,
      s_axi_arvalid => jtagtoaxim2s.arvalid,
      s_axi_awaddr => jtagtoaxim2s.awaddr,
      s_axi_awprot => jtagtoaxim2s.awprot,
      s_axi_awready => jtagtoaxis2m.awready,
      s_axi_awvalid => jtagtoaxim2s.awvalid,
      s_axi_bready => jtagtoaxim2s.bready,
      s_axi_bresp => jtagtoaxis2m.bresp,
      s_axi_bvalid => jtagtoaxis2m.bvalid,
      s_axi_rdata => jtagtoaxis2m.rdata,
      s_axi_rready => jtagtoaxim2s.rready,
      s_axi_rresp => jtagtoaxis2m.rresp,
      s_axi_rvalid => jtagtoaxis2m.rvalid,
      s_axi_wdata => jtagtoaxim2s.wdata,
      s_axi_wready => jtagtoaxis2m.wready,
      s_axi_wstrb => jtagtoaxim2s.wstrb,
      s_axi_wvalid => jtagtoaxim2s.wvalid,
      m_axi_aclk => clk,
      m_axi_aresetn => '1',
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
      reset => '0',
      m2s => m2s,
      s2m => s2m
      );
  
end arch;
