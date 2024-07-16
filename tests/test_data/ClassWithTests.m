classdef ClassWithTests < matlab.unittest.TestCase
    methods(Test, TestTags = {'Unit'})
        function testRunning(tc)
            %
            tc.assertTrue(true);
        end
    end
end
