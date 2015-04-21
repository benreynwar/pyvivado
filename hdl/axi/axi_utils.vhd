library ieee;
use ieee.std_logic_1164.all;

package axi_utils is

  constant axi_resp_OKAY: std_logic_vector(1 downto 0) := "00";
  constant axi_resp_EXOKAY: std_logic_vector(1 downto 0) := "01";
  constant axi_resp_SLVERR: std_logic_vector(1 downto 0) := "10";
  constant axi_resp_DECERR: std_logic_vector(1 downto 0) := "11";
  
  type axi4lite_m2s is
  record
    araddr: std_logic_vector(31 downto 0); 
    arprot: std_logic_vector(2 downto 0); -- not using
    arvalid: std_logic;
    awaddr: std_logic_vector(31 downto 0); 
    awprot: std_logic_vector(2 downto 0); -- not using
    awvalid: std_logic; 
    bready: std_logic;
    rready: std_logic;
    wdata: std_logic_vector(31 downto 0); 
    wstrb: std_logic_vector(3 downto 0); -- not using
    wvalid: std_logic;
  end record;
  constant AXI4LITE_M2S_WIDTH: integer := 32 + 3 + 1 + 32 + 3 + 1 + 1 + 1 + 32 + 4 + 1;

  type axi4lite_s2m is
  record
    arready: std_logic;
    awready: std_logic; 
    bresp: std_logic_vector(1 downto 0);
    bvalid: std_logic;
    rdata: std_logic_vector(31 downto 0);
    rresp: std_logic_vector(1 downto 0);
    rvalid: std_logic;
    wready: std_logic;
  end record;
  constant AXI4LITE_S2M_WIDTH: integer := 1 + 1 + 2 + 1 + 32 + 2 + 1 + 1;

  constant DEFAULT_AXI4LITE_S2M: axi4lite_s2m := (
    arready => '1',
    awready => '1',
    bresp => AXI_RESP_OKAY,
    bvalid =>'0',
    rdata => (others => '0'),
    rresp => AXI_RESP_OKAY,
    rvalid => '0',
    wready => '1'
    );

  constant MAX_N_SLAVE_IDS: natural := 11;
  subtype slave_id is integer range 0 to 65535;
  type array_of_slave_id is array(MAX_N_SLAVE_IDS-1 downto 0) of slave_id;
  type array_of_axi4lite_m2s is array(integer range <>) of axi4lite_m2s;
  type array_of_axi4lite_s2m is array(integer range <>) of axi4lite_s2m;

  function axi4lite_s2m_to_slv(input: axi4lite_s2m) return std_logic_vector;
  function axi4lite_s2m_from_slv(input: std_logic_vector) return axi4lite_s2m;
  function array_of_axi4lite_s2m_to_slv(input: array_of_axi4lite_s2m) return std_logic_vector;
  function array_of_axi4lite_s2m_from_slv(input: std_logic_vector) return array_of_axi4lite_s2m;

  function axi4lite_m2s_to_slv(input: axi4lite_m2s) return std_logic_vector;
  function axi4lite_m2s_from_slv(input: std_logic_vector) return axi4lite_m2s;
  function array_of_axi4lite_m2s_to_slv(input: array_of_axi4lite_m2s) return std_logic_vector;
  function array_of_axi4lite_m2s_from_slv(input: std_logic_vector) return array_of_axi4lite_m2s;

end axi_utils;

package body axi_utils is

  function axi4lite_m2s_to_slv(input: axi4lite_m2s) return std_logic_vector is
    variable output: std_logic_vector(AXI4LITE_M2S_WIDTH-1 downto 0);
  begin
    output(110 downto 79) := input.araddr;
    output(78 downto 76) := input.arprot;
    output(75) := input.arvalid;
    output(74 downto 43) := input.awaddr;
    output(42 downto 40) := input.awprot;
    output(39) := input.awvalid;
    output(38) := input.bready;
    output(37) := input.rready;
    output(36 downto 5) := input.wdata;
    output(4 downto 1) := input.wstrb;
    output(0) := input.wvalid;
    return output;
  end function;

  function axi4lite_m2s_from_slv(input: std_logic_vector) return axi4lite_m2s is
    variable output: axi4lite_m2s;
    variable shifted: std_logic_vector(AXI4LITE_M2S_WIDTH-1 downto 0);
  begin
    shifted := input;
    output.araddr := shifted(110 downto 79);
    output.arprot := shifted(78 downto 76);
    output.arvalid := shifted(75);
    output.awaddr := shifted(74 downto 43);
    output.awprot := shifted(42 downto 40);
    output.awvalid := shifted(39);
    output.bready := shifted(38);
    output.rready := shifted(37);
    output.wdata := shifted(36 downto 5);
    output.wstrb := shifted(4 downto 1);
    output.wvalid := shifted(0);
    return output;
  end function;

  function array_of_axi4lite_m2s_to_slv(input: array_of_axi4lite_m2s)
    return std_logic_vector is
    constant W: positive := AXI4LITE_M2S_WIDTH;
    variable output: std_logic_vector((input'HIGH-input'LOW+1)*W-1 downto 0);
  begin
    for ii in input'range loop
      output((ii-input'low+1)*W-1 downto (ii-input'low)*W) := axi4lite_m2s_to_slv(input(ii));
    end loop;
    return output;
  end function;

  function array_of_axi4lite_m2s_from_slv(input: std_logic_vector)
  return array_of_axi4lite_m2s is
    constant W: positive := AXI4LITE_M2S_WIDTH;
    variable output: array_of_axi4lite_m2s((input'HIGH+1-input'LOW)/W-1 downto 0);
  begin
    for ii in output'range loop
     output(ii) := axi4lite_m2s_from_slv(input((ii+1)*W-1+input'LOW downto ii*W+input'LOW));
    end loop;
    return output;
  end function;
  
  function axi4lite_s2m_to_slv(input: axi4lite_s2m) return std_logic_vector is
    variable output: std_logic_vector(AXI4LITE_S2M_WIDTH-1 downto 0);
  begin
    output(40) := input.arready;
    output(39) := input.awready;
    output(38 downto 37) := input.bresp;
    output(36) := input.bvalid;
    output(35 downto 4) := input.rdata;
    output(3 downto 2) := input.rresp;
    output(1) := input.rvalid;
    output(0) := input.wready;
    return output;
  end function;
  
  function axi4lite_s2m_from_slv(input: std_logic_vector) return axi4lite_s2m is
    variable output: axi4lite_s2m;
    variable shifted: std_logic_vector(AXI4LITE_S2M_WIDTH-1 downto 0);
  begin
    shifted := input;
    output.arready := shifted(40);
    output.awready := shifted(39);
    output.bresp := shifted(38 downto 37);
    output.bvalid := shifted(36);
    output.rdata := shifted(35 downto 4);
    output.rresp := shifted(3 downto 2);
    output.rvalid := shifted(1);
    output.wready := shifted(0);
    return output;
  end function;
  
  function array_of_axi4lite_s2m_to_slv(input: array_of_axi4lite_s2m)
    return std_logic_vector is
    constant W: positive := AXI4LITE_S2M_WIDTH;
    variable output: std_logic_vector((input'HIGH-input'LOW+1)*W-1 downto 0);
  begin
    for ii in input'range loop
      output((ii-input'LOW+1)*W-1 downto (ii-input'LOW)*W) := axi4lite_s2m_to_slv(input(ii));
    end loop;
    return output;
  end function;

  function array_of_axi4lite_s2m_from_slv(input: std_logic_vector)
  return array_of_axi4lite_s2m is
    constant W: positive := AXI4LITE_S2M_WIDTH;
    variable output: array_of_axi4lite_s2m((input'HIGH+1-input'LOW)/W-1 downto 0);
  begin
    for ii in output'range loop
     output(ii) := axi4lite_s2m_from_slv(input((ii+1)*W-1+input'LOW downto ii*W+input'LOW));
    end loop;
    return output;
  end function;

  
end package body;
