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
check_range(lo, hi);
y = min(max(x, lo), hi);
end
