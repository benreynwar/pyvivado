module TestB
  #(
    int DATA_WIDTH = -1
    )
   (
    input logic i_valid,
    input logic [DATA_WIDTH-1: 0] i_data,
    output logic o_valid,
    output logic [DATA_WIDTH-1: 0] o_data
    );

   assign o_valid = i_valid;
   assign o_data = i_data;
   
endmodule
