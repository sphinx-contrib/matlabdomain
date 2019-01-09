classdef ClassBySource
    % Class which should be printed by source

    methods
        function testC(obj)
            % testC function
            disp('testC');
        end

        function testB(obj)
            % testB function
            disp('testB');
        end

        function testA(obj)
            % testA function
            disp('testA');
        end
    end
    
end

