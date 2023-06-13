from sphinxcontrib.mat_parser import transform_empty_class_methods


def test_transform_empty_class_methods():
    code = """
classdef ClassFolder
% A class in a folder
    methods (Static)
    % skip comments above
        retv = a_static_func(args) % skip comments inline
        function b = foo()
            the_body = 10;
        end
        function [a,b] = bar(c)
            %the_bod
            retv = sdkl;
        end
    end
end
"""
    fixed_code = transform_empty_class_methods(code)
    pass


"""
[sdjs] = fsdjk()
fsdjk
dsjk = skdj
[sdjs, asdjk] = fsdjk()


  %

"""


def test_blob():
    code = """
classdef TestFibonacci < matlab.unittest.TestCase
    % Test of MATLAB unittest method attributes

    methods(Test)

        function compareFirstThreeElementsToExpected(tc)
            % Test case that compares first three elements

            f = fibonacci(3, 0);
            expected = [1; 1; 2];

            verifyEqual(tc, f, expected)
        end

    end
end
"""
    fixed_code = transform_empty_class_methods(code)
    pass
