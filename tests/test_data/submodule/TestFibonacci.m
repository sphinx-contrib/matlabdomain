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