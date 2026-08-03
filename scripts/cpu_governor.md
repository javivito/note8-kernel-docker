# CPU Governor — Note 8 (Exynos 8895)

## Cores

| Cores | CPU | Tipo | Frecuencias disponibles |
|---|---|---|---|
| cpu0-3 | Cortex-A53 | Eficiencia | hasta 1690 MHz |
| cpu4-7 | Cortex-A73 | Rendimiento | hasta 2314 MHz |

## Governors disponibles

| Governor | Descripción |
|---|---|
| `interactive` | Sube bajo carga, baja en idle. **Por defecto.** |
| `performance` | Siempre al máximo. Más calor, más consumo. |
| `userspace` | Frecuencia manual fija. |
| `blu_active` | Variante Samsung de interactive. |

## Ver frecuencia actual

```sh
# Cores de eficiencia (A53)
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq

# Cores de rendimiento (A73)
cat /sys/devices/system/cpu/cpu4/cpufreq/scaling_cur_freq
```

## Cambiar governor (solo sesión actual, se pierde al reiniciar)

### Performance — máximo siempre

```sh
for cpu in 0 1 2 3 4 5 6 7; do
  echo performance > /sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_governor
done
```

### Volver a interactive (por defecto)

```sh
for cpu in 0 1 2 3 4 5 6 7; do
  echo interactive > /sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_governor
done
```

### Frecuencia fija intermedia (userspace)

```sh
for cpu in 4 5 6 7; do
  echo userspace > /sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_governor
  echo 1807000 > /sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_setspeed
done
```

## Notas

- En idle con `interactive` los A73 bajan a 741 MHz — es normal, no es throttling.
- El throttling térmico ocurre cuando carga el móvil + carga CPU simultáneamente.
- Para un servidor siempre activo, `performance` da menor latencia de respuesta.
- Los cambios son temporales. Para hacerlos permanentes habría que añadirlos al `service.d` de Magisk.
