function output = nested_fun(input)
% This function has a nested inner function
%
% :param input: input arg
% :return: output

%% inner function doesn't get documented
function x = inner_fun()
% to document the inner function call
% ``sphinxcontrib.mat_types.MatFunction()`` recursively
x = 0
end
