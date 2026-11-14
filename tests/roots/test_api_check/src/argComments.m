function y = argComments(x, opts)
%ARGCOMMENTS Arguments documented by arguments-block comments.
arguments
    x double % the data
    % the tolerance
    opts.Tol (1,1) double = 1e-6
end
arguments (Output)
    y double % the result
end
y = x;
end
