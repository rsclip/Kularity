rem Bypass "Terminate Batch Job" prompt.
if "%~1"=="-FIXED_CTRL_C" (
   REM Remove the -FIXED_CTRL_C parameter
   SHIFT
) ELSE (
   REM Run the batch with <NUL and -FIXED_CTRL_C
   CALL <NUL %0 -FIXED_CTRL_C %*
   GOTO :EOF
)

del /f /q /s test && cls && py main.py --il 2 --ssub teenagers --ul 5 --sl 5 --fl --dir test --normalize -5 100 --noInput --formatJSON --ucl 500
