function varargout = f_with_output_repeating_argument_block(a1)
  arguments (Input)
      a1 (1,1) double {mustBePositive} % Positive scalar input
  end
    arguments (Output,Repeating)
        varargout (1,1) double {mustBePositive} % Repeating outputs
    end

    varargout = {a1, a1 + 1};
end
