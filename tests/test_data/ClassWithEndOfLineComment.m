classdef ClassWithEndOfLineComment
    methods
        % No spaces between the end of line and the comment caused Sphinx to crash
        function test1(this)% Does this crash
        end

        function test2(this) % Or does this crash
        end
    end
end
