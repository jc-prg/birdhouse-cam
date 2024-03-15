<?php
// File: index.php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);
$timestamp = time();

// File to store the IPv6 address and birdhouse identifier
$ipv6_file = 'ipv6_address.txt';

// Function to get the stored IPv6 addresses and birdhouse identifiers
function getStoredIPv6Addresses($file) {
    if (file_exists($file)) {
        $contents = file_get_contents($file);
        if ($contents !== false) {
            return json_decode($contents, true);
        }
    }
    return [];
}

// Function to save the IPv6 address and birdhouse identifier to file
function saveIPv6Address($file, $ipv6, $birdhouse_identifier, $port_http, $port_api) {
    $birdhouse_info = array(
        "id" =>   $birdhouse_identifier,
        "ipv6" => $ipv6,
        "http" => $port_http,
        "api" =>  $port_api
        );
    $stored_addresses = getStoredIPv6Addresses($file);
    $stored_addresses[$birdhouse_identifier] = $birdhouse_info;
    file_put_contents($file, json_encode($stored_addresses));

    echo json_encode($birdhouse_info);
}
// Check if script is called with parameter to identify and save IPv6 address
if (isset($_GET['identify_ipv6']) && isset($_GET['identify_birdhouse'])) {
    // Get the IPv6 address and birdhouse identifier from the HTTP request
    echo json_encode($_GET);

    $client_ipv6 = $_GET['identify_ipv6'];
    $birdhouse_identifier = $_GET['identify_birdhouse'];
    $port_api  = $_GET['api'];
    $port_http = $_GET['http'];

    // Save the IPv6 address and birdhouse identifier to file
    saveIPv6Address($ipv6_file, $client_ipv6, $birdhouse_identifier, $port_http, $port_api);
    exit; // Stop script execution after saving IPv6 address
}

// Get the stored IPv6 addresses and birdhouse identifiers
$stored_addresses = getStoredIPv6Addresses($ipv6_file);

// If no stored addresses, display message
if (empty($stored_addresses)) {
    echo '<!DOCTYPE html>
    <html>
    <head>
        <meta name="theme-color" content="#000000"></meta>
        <meta name="apple-mobile-web-app-capable" content="yes"></meta>
        <meta name="apple-mobile-web-app-status-bar-style" content="black"></meta>
        <META name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=0.3, maximum-scale=1.0"></META>

        <link rel="apple-touch-icon"             href="favicon.png"></link>
        <link rel="apple-touch-icon-precomposed" href="favicon.png"></link>
        <link rel="stylesheet" type="text/css"   href="index.css"></link>

        <title>jc://birdhouse/</title>
    </head>
    <body style="background:#111111">
        <center>
            <h1 style="color:#EEEEEE">jc://birdhouse/</h1>
            <br/>&nbsp;
            <p style="color:#EEEEEE">
                Got no data from birdhouse server yet.
            </p>
        </center>
    </body>
    </html>';
} else {
    // Display links with stored data
    echo '<!DOCTYPE html>
    <html>
    <head>
        <meta name="theme-color" content="#000000"></meta>
        <meta name="apple-mobile-web-app-capable" content="yes"></meta>
        <meta name="apple-mobile-web-app-status-bar-style" content="black"></meta>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=0.3, maximum-scale=1.0"></meta>

        <link rel="apple-touch-icon"             href="favicon.png"></link>
        <link rel="apple-touch-icon-precomposed" href="favicon.png"></link>
        <link rel="stylesheet" type="text/css"   href="index.css"></link>

        <title>jc://birdhouse/</title>

        <script>
            var birdhouses = ' . json_encode($stored_addresses) . ';
            var timestamp = ' . $timestamp . ';
        </script>
    </head>
    <body>
        <center>
            <h1 style="color:#EEEEEE">jc://birdhouse/</h1>
            <br/>
            <p style="color:#EEEEEE">
            <img src="bird.gif" style="width:200px;" /><br/>
            <br/>&nbsp;<div id="birdhouses"></div></p>
        </center>
    <script src="index.js"></script>
    </body>
    </html>';
}
?>
