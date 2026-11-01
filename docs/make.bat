@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
if "%SPHINXAUTOBUILD%" == "" (
	set SPHINXAUTOBUILD=sphinx-autobuild
)
set SOURCEDIR=.
set BUILDDIR=_build
set SPHINXPROJ=sphinxcontrib-matlabdomain

if "%1" == "" goto help
if "%1" == "livehtml" goto livehtml

%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found. Make sure you have Sphinx
	echo.installed, then set the SPHINXBUILD environment variable to point
	echo.to the full path of the 'sphinx-build' executable. Alternatively you
	echo.may add the Sphinx directory to PATH.
	echo.
	echo.If you don't have Sphinx installed, grab it from
	echo.http://sphinx-doc.org/
	exit /b 1
)

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS%
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS%
goto end

REM Rebuild on every change and serve the HTML at http://127.0.0.1:8000.
REM The pages include files from the worked example, so watch it too.
:livehtml
%SPHINXAUTOBUILD% %SOURCEDIR% %BUILDDIR%\html --watch ..\examples\apidoc %SPHINXOPTS%

:end
popd
