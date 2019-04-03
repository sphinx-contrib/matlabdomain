function obj = f_with_function_variable(the_functions, ~)
    % Constructor functionVar functionVar
    % function[
    % function(
    % function;
    % function

    this = ['%', 'functionVar'] % functionVar
    % Determine the name and M-file location of the function handle.
    functionHandleInfo = functions(testFcn);
    self.Name = functionHandleInfo.function;
    if strcmp(functionHandleInfo.type, 'anonymous')
        % Anonymous function handles don't have an M-file location.
        self.Location = '';
    else
        self.Location = functionHandleInfo.file;
    end
end
