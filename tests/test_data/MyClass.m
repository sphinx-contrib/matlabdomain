classdef MyClass < handle
    %MYCLASS test class methods
    % MC = MYCLASS(A) returns an instance MC of MYCLASS with property A.
    properties
        a % a property
    end
    methods
        function mc = MyClass(a)
            mc.a = a
        end
        function c = mymethod(obj, b)
        %MYMETHOD a method in MYCLASS
        % C = MYMETHOD(OBJ, B) does stuff
            for n = 1:10
                if n > 5
                    c = obj.a + b
                else
                    c = obj.a + b^2
                end
            end
        end
    end
end
