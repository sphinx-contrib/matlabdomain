classdef ClassWithMethodAttributes
    % Class with different method attributes

    methods
        function test1(obj)
            % test1 function
            disp('test1');
        end
    end

    methods (Access = private)
        function test2(obj)
            % test2 function
            disp('test2');
        end
    end

    methods (Access = 'private')
        function test3(obj)
            % test3 function
            disp('test3');
        end
    end

    methods (Access = ?OtherClass)
        function test4(obj)
            % test4 function
            disp('test4');
        end
    end

    methods (Access = {?OtherClass, ?pack.OtherClass2})
        function test5(obj)
            % test5 function
            disp('test5');
        end
    end
    
end

