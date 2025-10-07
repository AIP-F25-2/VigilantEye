// Azure Bicep template for VigilantEye Flask API
param location string = resourceGroup().location
param appName string = 'vigilanteye-api'
param environment string = 'prod'
param adminEmail string = 'admin@example.com'

// Variables
var appServiceName = '${appName}-${environment}'
var mysqlServerName = '${appName}-mysql-${environment}'
var mysqlDatabaseName = 'flaskapi'
var mysqlAdminLogin = 'mysqladmin'
var resourceTags = {
  Environment: environment
  Application: 'VigilantEye'
  ManagedBy: 'Bicep'
}

// MySQL Flexible Server
resource mysqlServer 'Microsoft.DBforMySQL/flexibleServers@2022-01-01' = {
  name: mysqlServerName
  location: location
  tags: resourceTags
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: mysqlAdminLogin
    administratorLoginPassword: mysqlAdminPassword
    version: '8.0.21'
    storage: {
      storageSizeGB: 20
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    maintenanceWindow: {
      customWindow: 'Disabled'
      dayOfWeek: 0
      startHour: 0
      startMinute: 0
    }
  }
}

// MySQL Database
resource mysqlDatabase 'Microsoft.DBforMySQL/flexibleServers/databases@2022-01-01' = {
  parent: mysqlServer
  name: mysqlDatabaseName
  properties: {
    charset: 'utf8'
    collation: 'utf8_unicode_ci'
  }
}

// MySQL Firewall Rule - Allow Azure Services
resource mysqlFirewallRule 'Microsoft.DBforMySQL/flexibleServers/firewallRules@2022-01-01' = {
  parent: mysqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: '${appServiceName}-plan'
  location: location
  tags: resourceTags
  sku: {
    name: 'B1'
    tier: 'Basic'
    size: 'B1'
    family: 'B'
    capacity: 1
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// App Service
resource appService 'Microsoft.Web/sites@2022-03-01' = {
  name: appServiceName
  location: location
  tags: resourceTags
  kind: 'app,linux,container'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|mcr.microsoft.com/appservice/samples/aspnetcore:latest'
      alwaysOn: false
      appSettings: [
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: 'https://index.docker.io'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_USERNAME'
          value: ''
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_PASSWORD'
          value: ''
        }
        {
          name: 'DOCKER_CUSTOM_IMAGE_NAME'
          value: '${appName}:latest'
        }
        {
          name: 'WEBSITES_PORT'
          value: '5000'
        }
        {
          name: 'DATABASE_URL'
          value: 'mysql+pymysql://${mysqlAdminLogin}:${mysqlAdminPassword}@${mysqlServer.properties.fullyQualifiedDomainName}:3306/${mysqlDatabaseName}'
        }
        {
          name: 'SECRET_KEY'
          value: secretKey
        }
        {
          name: 'JWT_SECRET_KEY'
          value: jwtSecretKey
        }
        {
          name: 'FLASK_ENV'
          value: 'production'
        }
      ]
    }
    httpsOnly: true
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${appServiceName}-insights'
  location: location
  tags: resourceTags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    Request_Source: 'rest'
    WorkspaceResourceId: logAnalyticsWorkspace.id
  }
}

// Log Analytics Workspace
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${appServiceName}-logs'
  location: location
  tags: resourceTags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Outputs
output appServiceName string = appService.name
output appServiceUrl string = 'https://${appService.properties.defaultHostName}'
output mysqlServerName string = mysqlServer.name
output mysqlConnectionString string = 'mysql+pymysql://${mysqlAdminLogin}:${mysqlAdminPassword}@${mysqlServer.properties.fullyQualifiedDomainName}:3306/${mysqlDatabaseName}'
