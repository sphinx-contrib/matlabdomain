classdef ClassWithEllipsisProperties < handle
    % stuff
    properties (Constant)
        A = 1 + 2 + 3 + ... my butt
            4 + 5; % an expression with ellipsis
        B = {'hello', 'bye'; ...
            'foo', 'bar';
            'this', 'that'
            'also' 'too'
            } % a cell array with ellipsis and other array notation
        C = ClassWithEllipsisProperties.B(2:end, 1) % using end inside array
        D = '...'; % String with line continuation
    end
end
