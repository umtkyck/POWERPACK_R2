/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body for HW_BO_POWERPACK_R2M1
  ******************************************************************************
  * @attention
  *
  * Power Pack Controller Firmware R2M1
  * - Relay Control (2 independent relays via GPIO_M1, GPIO_M2)
  * - Dimmer Control via I2C (GP8413)
  * - USB CDC for configuration
  *
  * Relay 1 controlled by GPIO_M1 (PB13)
  * Relay 2 controlled by GPIO_M2 (PB12)
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "usb_device.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "usbd_cdc_if.h"
#include <string.h>
#include <stdio.h>

// Debug message buffer
char debug_msg[128];
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
typedef struct {
    uint8_t relay1_state;     // Relay 1 state (GPIO_M1)
    uint8_t relay2_state;     // Relay 2 state (GPIO_M2)
    uint16_t dimmer1_value;   // 0-4095 (12-bit DAC)
    uint16_t dimmer2_value;   // 0-4095 (12-bit DAC)
    uint8_t dimmer1_enabled;
    uint8_t dimmer2_enabled;
} PowerPackState_t;

// Command definitions
#define CMD_SET_RELAY1          0x01  // Control Relay 1
#define CMD_SET_RELAY2          0x02  // Control Relay 2
#define CMD_SET_DIMMER1         0x03
#define CMD_SET_DIMMER2         0x04
#define CMD_GET_STATUS          0x05
#define CMD_ENABLE_DIMMER1      0x06
#define CMD_ENABLE_DIMMER2      0x07
#define CMD_DISABLE_DIMMER1     0x08
#define CMD_DISABLE_DIMMER2     0x09
#define CMD_GET_VERSION         0x0A

// Firmware version
#define FIRMWARE_VERSION_MAJOR  2
#define FIRMWARE_VERSION_MINOR  0
#define FIRMWARE_VERSION_PATCH  1
/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
#define GP8413_ADDRESS          0x58  // 7-bit address
#define GP8413_REG_CONFIG       0x02
#define GP8413_REG_DAC1         0x10
#define GP8413_REG_DAC2         0x11

// GPIO Pin Definitions (based on actual main.h)
#define GPIO_M1_PIN             GPIO_M1_Pin      // PB13
#define GPIO_M1_PORT            GPIO_M1_GPIO_Port // GPIOB
#define GPIO_M2_PIN             GPIO_M2_Pin      // PB12
#define GPIO_M2_PORT            GPIO_M2_GPIO_Port // GPIOB
#define DIM_OUT_EN_1_PIN        DIM_OUT_EN_1_Pin // PB0
#define DIM_OUT_EN_1_PORT       DIM_OUT_EN_1_GPIO_Port // GPIOB
#define DIM_OUT_EN_2_PIN        DIM_OUT_EN_2_Pin // PB1
#define DIM_OUT_EN_2_PORT       DIM_OUT_EN_2_GPIO_Port // GPIOB
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
I2C_HandleTypeDef hi2c1;

TIM_HandleTypeDef htim3;

/* USER CODE BEGIN PV */
PowerPackState_t powerpack_state = {0};
uint8_t usb_rx_buffer[64];
uint8_t usb_tx_buffer[64];
volatile uint8_t usb_data_received = 0;

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_I2C1_Init(void);
static void MX_TIM3_Init(void);
/* USER CODE BEGIN PFP */
void PowerPack_Init(void);
void Set_Relay(uint8_t relay_num, uint8_t state);
void Set_Dimmer(uint8_t dimmer_num, uint16_t value);
void Enable_Dimmer(uint8_t dimmer_num, uint8_t enable);
HAL_StatusTypeDef GP8413_WriteRegister(uint8_t reg, uint16_t value);
void Process_USB_Command(uint8_t* data, uint16_t length);
void Send_Status_Response(void);
void Send_Version_Response(void);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_I2C1_Init();
  MX_USB_DEVICE_Init();
  MX_TIM3_Init();
  /* USER CODE BEGIN 2 */
  
  // Send boot message via USB CDC
  HAL_Delay(2000);  // Wait for USB to initialize
  
  sprintf(debug_msg, "\r\n=== PowerPack R2M1 v%d.%d.%d Started ===\r\n", 
          FIRMWARE_VERSION_MAJOR, FIRMWARE_VERSION_MINOR, FIRMWARE_VERSION_PATCH);
  CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
  HAL_Delay(100);
  
  sprintf(debug_msg, "System Clock: %lu MHz\r\n", HAL_RCC_GetHCLKFreq() / 1000000);
  CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
  HAL_Delay(100);
  
  sprintf(debug_msg, "Initializing PowerPack...\r\n");
  CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
  HAL_Delay(100);
  
  PowerPack_Init();
  
  sprintf(debug_msg, "PowerPack initialized successfully\r\n");
  CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
  HAL_Delay(100);
  
  sprintf(debug_msg, "Relay 1: %s, Relay 2: %s\r\n", 
          powerpack_state.relay1_state ? "ON" : "OFF",
          powerpack_state.relay2_state ? "ON" : "OFF");
  CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
  HAL_Delay(100);
  
  sprintf(debug_msg, "Ready for commands!\r\n");
  CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
  HAL_Delay(100);

  // Start timer for status updates
  HAL_TIM_Base_Start_IT(&htim3);

  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */

    // Process USB commands
	  // Process USB commands
	  // Process USB commands
	  if (usb_data_received) {
	    Process_USB_Command(usb_rx_buffer, 64);
	    usb_data_received = 0;
	  }

	  HAL_Delay(10);
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
  RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL6;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_1) != HAL_OK)
  {
    Error_Handler();
  }
  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_USB;
  PeriphClkInit.UsbClockSelection = RCC_USBCLKSOURCE_PLL;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief I2C1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_I2C1_Init(void)
{

  /* USER CODE BEGIN I2C1_Init 0 */

  /* USER CODE END I2C1_Init 0 */

  /* USER CODE BEGIN I2C1_Init 1 */

  /* USER CODE END I2C1_Init 1 */
  hi2c1.Instance = I2C1;
  hi2c1.Init.ClockSpeed = 100000;
  hi2c1.Init.DutyCycle = I2C_DUTYCYCLE_2;
  hi2c1.Init.OwnAddress1 = 0;
  hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c1.Init.OwnAddress2 = 0;
  hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN I2C1_Init 2 */

  /* USER CODE END I2C1_Init 2 */

}

/**
  * @brief TIM3 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM3_Init(void)
{

  /* USER CODE BEGIN TIM3_Init 0 */

  /* USER CODE END TIM3_Init 0 */

  TIM_ClockConfigTypeDef sClockSourceConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};

  /* USER CODE BEGIN TIM3_Init 1 */

  /* USER CODE END TIM3_Init 1 */
  htim3.Instance = TIM3;
  htim3.Init.Prescaler = 35999;
  htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim3.Init.Period = 4999 ;
  htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim3) != HAL_OK)
  {
    Error_Handler();
  }
  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim3, &sClockSourceConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim3, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM3_Init 2 */

  /* USER CODE END TIM3_Init 2 */

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
/* USER CODE BEGIN MX_GPIO_Init_1 */
/* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOB, DIM_OUT_EN_1_Pin|DIM_OUT_EN_2_Pin|GPIO_M2_Pin|GPIO_M1_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pins : DIM_OUT_EN_1_Pin DIM_OUT_EN_2_Pin GPIO_M2_Pin GPIO_M1_Pin */
  GPIO_InitStruct.Pin = DIM_OUT_EN_1_Pin|DIM_OUT_EN_2_Pin|GPIO_M2_Pin|GPIO_M1_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

/* USER CODE BEGIN MX_GPIO_Init_2 */
/* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */
/**
  * @brief Initialize Power Pack peripherals
  * @retval None
  */
void PowerPack_Init(void)
{
  // Initialize GP8413 DAC
  GP8413_WriteRegister(GP8413_REG_CONFIG, 0x0000);  // Default configuration

  // Initialize state
  powerpack_state.relay1_state = 0;
  powerpack_state.relay2_state = 0;
  powerpack_state.dimmer1_value = 0;
  powerpack_state.dimmer2_value = 0;
  powerpack_state.dimmer1_enabled = 0;
  powerpack_state.dimmer2_enabled = 0;

  // Set initial relay states (both OFF)
  Set_Relay(1, 0);
  Set_Relay(2, 0);

  // Set initial dimmer states
  Enable_Dimmer(1, 0);
  Enable_Dimmer(2, 0);
}

/**
  * @brief Control relay output
  * @param relay_num: Relay number (1 or 2)
  * @param state: Relay state (0 = OFF, 1 = ON)
  * @retval None
  */
void Set_Relay(uint8_t relay_num, uint8_t state)
{
  if (relay_num == 1) {
    // Control Relay 1 via GPIO_M1
    HAL_GPIO_WritePin(GPIO_M1_PORT, GPIO_M1_PIN, state ? GPIO_PIN_SET : GPIO_PIN_RESET);
    powerpack_state.relay1_state = state;
  } else if (relay_num == 2) {
    // Control Relay 2 via GPIO_M2
    HAL_GPIO_WritePin(GPIO_M2_PORT, GPIO_M2_PIN, state ? GPIO_PIN_SET : GPIO_PIN_RESET);
    powerpack_state.relay2_state = state;
  }
}

/**
  * @brief Set dimmer output value
  * @param dimmer_num: Dimmer number (1 or 2)
  * @param value: DAC value (0-4095)
  * @retval None
  */
void Set_Dimmer(uint8_t dimmer_num, uint16_t value)
{
  if (value > 4095) value = 4095;

  if (dimmer_num == 1) {
    GP8413_WriteRegister(GP8413_REG_DAC1, value);
    powerpack_state.dimmer1_value = value;
  } else if (dimmer_num == 2) {
    GP8413_WriteRegister(GP8413_REG_DAC2, value);
    powerpack_state.dimmer2_value = value;
  }
}

/**
  * @brief Enable/disable dimmer output
  * @param dimmer_num: Dimmer number (1 or 2)
  * @param enable: Enable state (0 = disabled, 1 = enabled)
  * @retval None
  */
void Enable_Dimmer(uint8_t dimmer_num, uint8_t enable)
{
  if (dimmer_num == 1) {
    HAL_GPIO_WritePin(DIM_OUT_EN_1_PORT, DIM_OUT_EN_1_PIN, enable ? GPIO_PIN_SET : GPIO_PIN_RESET);
    powerpack_state.dimmer1_enabled = enable;
  } else if (dimmer_num == 2) {
    HAL_GPIO_WritePin(DIM_OUT_EN_2_PORT, DIM_OUT_EN_2_PIN, enable ? GPIO_PIN_SET : GPIO_PIN_RESET);
    powerpack_state.dimmer2_enabled = enable;
  }
}

/**
  * @brief Write to GP8413 register
  * @param reg: Register address
  * @param value: 16-bit value to write
  * @retval HAL status
  */
HAL_StatusTypeDef GP8413_WriteRegister(uint8_t reg, uint16_t value)
{
  uint8_t data[3];
  data[0] = reg;
  data[1] = (value >> 8) & 0xFF;  // MSB
  data[2] = value & 0xFF;         // LSB

  return HAL_I2C_Master_Transmit(&hi2c1, GP8413_ADDRESS << 1, data, 3, HAL_MAX_DELAY);
}

/**
  * @brief Process USB command
  * @param data: Command data
  * @param length: Data length
  * @retval None
  */
void Process_USB_Command(uint8_t* data, uint16_t length)
{
  if (length < 2) return;

  uint8_t cmd = data[0];
  uint8_t param = data[1];
  uint16_t value = (data[2] << 8) | data[3];
  
  // Debug: Log received command
  sprintf(debug_msg, "CMD: 0x%02X, param: %d, value: %d\r\n", cmd, param, value);
  CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));

  switch (cmd) {
    case CMD_SET_RELAY1:
      Set_Relay(1, param);
      sprintf(debug_msg, "Relay 1 -> %s\r\n", param ? "ON" : "OFF");
      CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
      break;

    case CMD_SET_RELAY2:
      Set_Relay(2, param);
      sprintf(debug_msg, "Relay 2 -> %s\r\n", param ? "ON" : "OFF");
      CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
      break;

    case CMD_SET_DIMMER1:
      Set_Dimmer(1, value);
      sprintf(debug_msg, "Dimmer 1 -> %d\r\n", value);
      CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
      break;

    case CMD_SET_DIMMER2:
      Set_Dimmer(2, value);
      sprintf(debug_msg, "Dimmer 2 -> %d\r\n", value);
      CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
      break;

    case CMD_ENABLE_DIMMER1:
      Enable_Dimmer(1, 1);
      sprintf(debug_msg, "Dimmer 1 enabled\r\n");
      CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
      break;

    case CMD_ENABLE_DIMMER2:
      Enable_Dimmer(2, 1);
      sprintf(debug_msg, "Dimmer 2 enabled\r\n");
      CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
      break;

    case CMD_DISABLE_DIMMER1:
      Enable_Dimmer(1, 0);
      sprintf(debug_msg, "Dimmer 1 disabled\r\n");
      CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
      break;

    case CMD_DISABLE_DIMMER2:
      Enable_Dimmer(2, 0);
      sprintf(debug_msg, "Dimmer 2 disabled\r\n");
      CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
      break;

    case CMD_GET_STATUS:
      sprintf(debug_msg, "Status requested\r\n");
      CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
      Send_Status_Response();
      break;

    case CMD_GET_VERSION:
      sprintf(debug_msg, "Version requested\r\n");
      CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
      Send_Version_Response();
      break;
      
    default:
      sprintf(debug_msg, "Unknown command: 0x%02X\r\n", cmd);
      CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
      break;
  }
}

/**
  * @brief Send status response via USB
  * @retval None
  */
void Send_Status_Response(void)
{
  uint8_t response[8];
  response[0] = CMD_GET_STATUS;
  response[1] = powerpack_state.relay1_state;
  response[2] = powerpack_state.relay2_state;
  response[3] = (powerpack_state.dimmer1_value >> 8) & 0xFF;
  response[4] = powerpack_state.dimmer1_value & 0xFF;
  response[5] = (powerpack_state.dimmer2_value >> 8) & 0xFF;
  response[6] = powerpack_state.dimmer2_value & 0xFF;
  response[7] = (powerpack_state.dimmer1_enabled << 1) | powerpack_state.dimmer2_enabled;

  CDC_Transmit_FS(response, 8);
}

/**
  * @brief Send version response via USB
  * @retval None
  */
void Send_Version_Response(void)
{
  uint8_t response[8];
  response[0] = CMD_GET_VERSION;
  response[1] = FIRMWARE_VERSION_MAJOR;
  response[2] = FIRMWARE_VERSION_MINOR;
  response[3] = FIRMWARE_VERSION_PATCH;
  response[4] = 0; // Reserved
  response[5] = 0; // Reserved
  response[6] = 0; // Reserved
  response[7] = 0; // Reserved

  CDC_Transmit_FS(response, 8);
}

/**
  * @brief Timer callback for periodic status updates
  * @param htim: Timer handle
  * @retval None
  */
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
  if (htim->Instance == TIM3) {
    // Send periodic status update every 5 seconds (reduced frequency)
    static uint8_t counter = 0;
    counter++;
    if (counter >= 5) {  // 5 timer interrupts = 5 seconds
      counter = 0;
      Send_Status_Response();
    }
  }
}

/**
  * @brief USB data received callback
  * @param Buf: Data buffer
  * @param Len: Data length
  * @retval None
  */
void USB_DataReceived(uint8_t* Buf, uint32_t Len)
{
  if (Len > 0 && Len <= 64) {
	// Debug: Log received data
	sprintf(debug_msg, "RX: %lu bytes [", Len);
	CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
	
	for(uint32_t i = 0; i < Len && i < 8; i++) {
	  sprintf(debug_msg, " %02X", Buf[i]);
	  CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
	}
	sprintf(debug_msg, " ]\r\n");
	CDC_Transmit_FS((uint8_t*)debug_msg, strlen(debug_msg));
	HAL_Delay(50);
	
	// Copy received data to processing buffer
	memcpy(usb_rx_buffer, Buf, Len);
	usb_data_received = 1;

	// Process command immediately
	Process_USB_Command(Buf, Len);

	// Debug echo - gelen veriyi geri gönder
	uint8_t echo[8] = {0xEE, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
	if (Len >= 1) echo[1] = Buf[0];
	if (Len >= 2) echo[2] = Buf[1];
	if (Len >= 3) echo[3] = Buf[2];
	if (Len >= 4) echo[4] = Buf[3];

	CDC_Transmit_FS(echo, 8);
  }
}
/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
