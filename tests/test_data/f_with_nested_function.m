function output = f_with_nested_function(input)
% This function has a nested inner function
%
% :param input: input arg
% :return: output

output = inner_fun(input);

end

%% inner function doesn't get documented
function y = inner_fun(x)
% to document the inner function call
% ``sphinxcontrib.mat_types.MatFunction()`` recursively
y = 2*x;
end