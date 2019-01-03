classdef ClassWithMethodAttributes
    % Class with different method attributes

    methods
        function testNormal(obj)
            % testNormal function
            disp('testNormal');
        end
    end

    methods (Access = public)
        function testPublic(obj)
            % testPublic function
            disp('testPublic');
        end
    end

    methods (Access = protected)
        function testProtected(obj)
            % testProtected function
            disp('testProtected');
        end
    end

    methods (Access = private)
        function testPrivate1(obj)
            % testPrivate1 function
            disp('testPrivate1');
        end
    end

    methods (Access = 'private')
        function testPrivate2(obj)
            % testPrivate2 function
            disp('testPrivate2');
        end
    end

    methods (Hidden)
        function testHidden(obj)
            % testHidden function
            disp('testHidden');
        end
    end

    methods (Static)
        function testStatic()
            % testStatic function
            disp('testStatic');
        end
    end

    methods (Access = ?OtherClass)
        function testFriend1(obj)
            % testFriend1 function
            disp('testFriend1');
        end
    end

    methods (Access = {?OtherClass, ?pack.OtherClass2})
        function testFriend2(obj)
            % testFriend2 function
            disp('testFriend2');
        end
    end
    
end

