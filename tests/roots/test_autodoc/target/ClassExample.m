classdef ClassExample < handle
    % Example class
    %
    % ClassExample Properties:
    %   a - first property of ClassExample
    %   b - second property of ClassExample
    %   c - third property of ClassExample
    % ClassExample Methods:
    %   ClassExample - the constructor and a reference to mymethod()
    %   mymethod - a method in ClassExample
    %
    % See also BaseClass, baseFunction, b, unknownEntity, mymethod,
    % package.ClassBar.bars, package.ClassBar.doFoo.

    properties
        a (1,:) {mustBeScalarOrEmpty}  = 42 % a property
        b = 10 % a property with default value
        c = [10;
            20;
            30]; % a property with multiline default value
    end
    methods
        function mc = ClassExample(a)
            % Links to fully qualified names package.ClassBar.foos,
            % package.ClassBar.doBar, and ClassExample.mymethod.
            mc.a = a;
        end

        function c = mymethod(obj, b)
            % A method in :class:`ClassExample`
            %
            % :param b: an input to :meth:`mymethod`
            for n = 1:10
                if n > 5
                    c = obj.a + b;
                else
                    c = obj.a + b^2;
                end
            end
        end
    end
end
