classdef ClassWithBuiltinProperties < handle
    % Class with properties that overload a builtin
    properties
        omega (1,:) {mustBeText} % a property
        alpha % a property overloading a builtin
        gamma (1,:) {mustBeScalarOrEmpty} % a property overloading a builtin with validation
        beta (1,:) {mustBeScalarOrEmpty} % another overloaded property
    end
end
