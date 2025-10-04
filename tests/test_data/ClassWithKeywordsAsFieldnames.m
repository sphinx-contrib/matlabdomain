classdef ClassWithKeywordsAsFieldnames
   % Class that uses keywords as fieldnames, i.e preceded by a dot and not
   % followed by a word break.
   properties
      a
      b
      c
   end

   methods
      function obj = ClassWithKeywordsAsFieldnames()
         % In MATLAB you can use `keywords` as fieldnames.
         obj.a = pkg.arguments.end;
         obj.b = pkg.otherwise.if;
         obj.c = pkg.persisent.try.while;
      end

      function d = calculate(obj)
         % Returns the value of `d`
         d = obj.a + obj.b + obj.c;
      end
   end
end
