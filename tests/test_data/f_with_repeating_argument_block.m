function s = f_with_repeating_argument_block(a, varargin)
  arguments (Input)
      a (1,1) double {mustBePositive} % Positive scalar input
  end
    arguments (Repeating)
        varargin (1,1) double {mustBePositive} % Repeating positive scalar
    end

    arguments (Output)
        s (1,1) double
    end

    s = sum([a, varargin{:}]);
end
