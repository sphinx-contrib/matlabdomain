function y = clamp(x, lo, hi)
% CLAMP Limit X to the range [LO, HI] (a global function).
%
%   Inputs:
%
%   * x - Values
%   * lo - Lower limit
%   * hi - Upper limit, at least LO
%
%   Outputs:
%
%   * y - X with values below LO set to LO and above HI set to HI
%
%   Example::
%
%      y = clamp([-1 0.5 2], 0, 1)   % [0 0.5 1]
check_range(lo, hi);
y = min(max(x, lo), hi);
end
