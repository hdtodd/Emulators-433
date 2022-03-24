#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <pigpio.h>

#define DELAY_US 25000

int main(int argc, char *argv[])
{
  gpioPulse_t pulse[2];
  uint32_t t0, t1, diffTick, expectedDelta;
  int k, ret, wave_id, testClock;
  float ratio;
  unsigned cfgMicros, cfgPeripheral;

  testClock = -1;  /* -1: test both configurations; 0: test PWM; 1: test PCM */

  if ( 1 < argc ) {
    if (!strcmp(argv[1], "pcm"))
      testClock = 1;
    else if (!strcmp(argv[1], "pwm"))
      testClock = 0;
    else
      testClock = atoi(argv[1]);
    if (testClock)
      testClock = 1;
  }

  for ( cfgPeripheral = 0; cfgPeripheral < 2; ++cfgPeripheral ) {
    if ( !( testClock == -1 || testClock == cfgPeripheral ) )
      continue;

    cfgMicros = 5;
    fprintf(stdout, "testing %s clock\n", (cfgPeripheral ? "PCM" : "PWM") );

    gpioCfgClock(cfgMicros, cfgPeripheral, 0);
    if (gpioInitialise() < 0)
    {
      fprintf(stderr, "pigpio initialisation failed.\n");
      return (cfgPeripheral+1)*10;
    }

    for ( k = 0; k < 2; ++k ) {
      pulse[k].gpioOn = 0;
      pulse[k].gpioOff = 0;
      pulse[k].usDelay = DELAY_US;
    }

    ret = gpioWaveAddNew();
    if (ret) {
      fprintf(stderr, "error at gpioWaveAddNew()\n");
      return 1;
    }
    ret = gpioWaveAddGeneric(2, pulse);
    if (ret != 2) {
      fprintf(stderr, "error at gpioWaveAddGeneric()\n");
      return 2;
    }
    wave_id = gpioWaveCreate();
    if (wave_id < 0) {
      fprintf(stderr, "error at gpioWaveCreate()\n");
      return 3;
    }

    ret = gpioWaveTxSend(wave_id, PI_WAVE_MODE_ONE_SHOT );
    t0 = gpioTick();
    if (ret <= 0) {
      fprintf(stderr, "error at gpioWaveTxSend()\n");
      return 4;
    }

    while ( gpioWaveTxBusy() ) {
      gpioDelay(500);
    }
    t1 = gpioTick();

    /*gpioWaveTxStop();*/
    gpioWaveClear();
    gpioTerminate();

    diffTick = t1 - t0;
    expectedDelta = DELAY_US + DELAY_US;
    ratio = (float)(diffTick) / (float)(expectedDelta);

    fprintf(stdout, "  delta = %u, expected = %u, ratio = %f\n", diffTick, expectedDelta, ratio);
    if ( 0.8F <= ratio && ratio <= 1.5F )
      fprintf(stdout, "  clock is OK\n");
    else if ( 1.8F <= ratio && ratio <= 2.2F )
      fprintf(stdout, "  clock is at half speed. all delays are doubled!\n");
    else
      fprintf(stdout, "  clock is corrupt!\n");
  }

  return 0;
}

