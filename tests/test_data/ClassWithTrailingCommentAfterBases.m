classdef ClassWithTrailingCommentAfterBases < handle & my.super.Class   % comment after bases
    % test class methods
    %
    % :param a: the input to :class:`ClassWithTrailingCommentAfterBases`

    properties
        a % a property
    end
    methods
        function mc = ClassWithTrailingCommentAfterBases(a)
            mc.a = a
        end
        function c = mymethod(obj, b)
        % a method in :class:`ClassWithTrailingCommentAfterBases`
        %
        % :param b: an input to :meth:`mymethod`

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
