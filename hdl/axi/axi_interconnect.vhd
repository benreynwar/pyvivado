-- -*- vhdl -*- 

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.axi_utils.all;
use work.pyvivado_utils.all;

-- We assume that the first high 16 bits of the address specify which slave
-- and the low 16 bits specify an address within a slave.
entity axi_interconnect is
  generic (
    SLAVE_IDS: array_of_slave_id;
    N_SLAVES: positive
    );
  port (
    clk: in std_logic;
    reset: in std_logic;
    -- Master interfaces to slaves
    o_s: out array_of_axi4lite_m2s(N_SLAVES-1 downto 0);
    i_s: in array_of_axi4lite_s2m(N_SLAVES-1 downto 0);
    -- Slave interface to master.
    i_m: in axi4lite_m2s;
    o_m: out axi4lite_s2m
    );
end axi_interconnect;

architecture arch of axi_interconnect is
  -- Ready to read/write.  We are not currently waiting for a
  -- response from a slave.
  -- We assume all slaves are always ready to read/write.
  signal m_waiting_for_read_response: std_logic;
  signal n_ready_to_read: std_logic;
  signal m_ready_to_write: std_logic;
  -- The id of the slave we are trying to start a read from.
  signal n_read_component_address: unsigned(15 downto 0);
  -- The index of the slave we last tried to read from.
  signal m_last_read_index: integer range 0 to 65535;
  -- The id of the slave we are trying to write to.
  signal n_write_component_address: unsigned(15 downto 0);
  -- The id of the last slave we tried to write to.
  signal m_write_component_address: unsigned(15 downto 0);
  -- The index of the slave we last tried to write to.
  signal m_last_write_index: integer range 0 to 65535;
  -- The address local to the slave where we're reading from.
  signal n_read_address: std_logic_vector(31 downto 0);
  -- The address local to the slave where we're writing to.
  signal n_write_address: std_logic_vector(31 downto 0);
  
  constant SIXTEEN_ZEROS: std_logic_vector(15 downto 0) := (others => '0');
  -- Intermediate for calculating valid_X_component
  signal is_reading_by_index: std_logic_vector(N_SLAVES-1 downto 0);
  signal is_writing_by_index: std_logic_vector(N_SLAVES-1 downto 0);
  -- Whether the slave specified by the address exists.
  signal valid_read_component: std_logic;
  signal valid_write_component: std_logic;
  -- Set to '1' the clock cycle after we try to read/write to a bad slave.
  signal m_bad_read_component_address: std_logic;
  signal m_bad_write_component_address: std_logic;
begin

  n_write_address <= SIXTEEN_ZEROS & i_m.awaddr(15 downto 0);
  n_write_component_address <= unsigned(i_m.awaddr(31 downto 16))
                               when i_m.awvalid = '1' else
                               m_write_component_address;

  n_read_address <= SIXTEEN_ZEROS & i_m.araddr(15 downto 0);
  n_read_component_address <= unsigned(i_m.araddr(31 downto 16));

  -- Create inputs to slaves from master inputs.
  loop_slaves: for si in 0 to N_SLAVES-1 generate
    is_reading_by_index(si) <= '1' when n_read_component_address = SLAVE_IDS(si)
                               else '0';
    is_writing_by_index(si) <= '1' when n_write_component_address = SLAVE_IDS(si)
                               else '0';
    o_s(si).araddr <= n_read_address;
    o_s(si).arvalid <= i_m.arvalid when is_reading_by_index(si) = '1' else
                       '0';
    o_s(si).awaddr <= n_write_address;
    o_s(si).awvalid <= i_m.awvalid when is_writing_by_index(si) = '1' else
                    '0';
    o_s(si).wdata <= i_m.wdata;
    o_s(si).wvalid <= i_m.wvalid when is_writing_by_index(si) = '1' else
                      '0';
    o_s(si).bready <= '1' when is_writing_by_index(si) = '1' and m_ready_to_write = '0' else
                      '0';
    o_s(si).rready <= '1' when is_reading_by_index(si) = '1' and n_ready_to_read = '0' else
                      '0';
  end generate;
  
  -- Create outputs to master from inputs from slaves.
  o_m.arready <= n_ready_to_read;
  o_m.awready <= '1';
  o_m.bresp <= axi_resp_DECERR when m_bad_write_component_address = '1' else
               i_s(m_last_write_index).bresp;
  o_m.bvalid <= '1' when m_bad_write_component_address = '1' else
                i_s(m_last_write_index).bvalid;
  o_m.rdata <= i_s(m_last_read_index).rdata;
  o_m.rresp <= axi_resp_DECERR when m_bad_read_component_address = '1' else
               i_s(m_last_read_index).bresp;
  o_m.rvalid <= '1' when m_bad_read_component_address = '1' else
                i_s(m_last_read_index).rvalid;
  -- Always be ready to be written to even if we're waiting for response.
  o_m.wready <= '1'; 

  valid_read_component <= or_slv(is_reading_by_index);
  valid_write_component <= or_slv(is_writing_by_index);
  
  n_ready_to_read <= '1' when i_s(m_last_read_index).rvalid = '1' else
                     not m_waiting_for_read_response;

  process(clk)
  begin
    if rising_edge(clk) then
      m_bad_read_component_address <= '0';
      m_bad_write_component_address <= '0';
      if (reset = '1') then
        m_waiting_for_read_response <= '0';
        m_ready_to_write <= '1';
        m_last_write_index <= 0;
        m_last_read_index <= 0;
      else
        m_waiting_for_read_response <= not n_ready_to_read;
        -- Receive a command to write.
        -- Don't worry about whether we're ready.
        -- We don't want to get stuck just because a slave fails to send a
        -- write response.
        if (i_m.awvalid = '1') then
          if (valid_write_component = '1') then
            m_last_write_index <= get_index_of_first_one(is_writing_by_index);
            m_write_component_address <= n_write_component_address;
            m_ready_to_write <= '0';
          else
            m_bad_write_component_address <= '1';
          end if;
        end if;
        -- Receive a command to read.
        if (i_m.arvalid = '1') and (n_ready_to_read = '1') then
          if (valid_read_component = '1') then
            m_last_read_index <= get_index_of_first_one(is_reading_by_index);
            m_waiting_for_read_response <= '1';
          else
            m_bad_read_component_address <= '1';
          end if;
        end if;
        -- If we get response back then get ready to take a new command.
        if (m_ready_to_write = '0') and (i_s(m_last_write_index).bvalid = '1') then
          m_ready_to_write <= '1';
        end if;
      end if;
    end if;
  end process;
  
end arch;
