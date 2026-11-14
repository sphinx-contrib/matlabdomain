function [y, info] = good(x, n, opts)
%GOOD A fully documented function.
%
% Inputs:
%   x - the data
%   n - a count
%
% Outputs:
%   y - the result
%   info - details
%
% Name-Value Arguments:
%   Mode - the mode
arguments
    x
    n = 1
    opts.Mode = "a"
end
y = x;
info = n;
end
