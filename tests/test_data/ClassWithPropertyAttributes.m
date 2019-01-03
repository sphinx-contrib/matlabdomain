classdef ClassWithPropertyAttributes
    % Class with different property attributes

    properties
        testNormal % Normal public property
    end

    properties (Access = public)
        testPublic % Public property
    end

    properties (Access = protected)
        testProtected % Protected property
    end

    properties (Access = private)
        testPrivate % Private property
    end

    properties (GetAccess = public, SetAccess = protected)
        testGetPublic % Get only public property
    end

    properties (GetAccess = protected, SetAccess = private)
        testGetProtected % Get only protected property
    end

    properties (GetAccess = private, SetAccess = private)
        testGetPrivate % Private property
    end

    properties (Constant)
        TEST_CONSTANT % Constant property
    end

    properties (Access = protected, Constant)
        TEST_CONSTANT_PROTECTED % Protected constant property
    end

    properties (Dependent)
        testDependent % Dependent property
    end

    properties (Hidden)
        testHidden % Hidden property
    end
    
end

