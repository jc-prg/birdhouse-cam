<?php
// File: index.php


// File to store the IPv6 address
$ipv6_file = 'ipv6_address.txt';

// Function to get the stored IPv6 address
function getStoredIPv6Address($file) {
    if (file_exists($file)) {
        return file_get_contents($file);
    }
    return false;
}

// Function to save the IPv6 address to file using fwrite
function saveIPv6Address_2($file, $ipv6) {
    $handle = fopen($file, 'w'); // Open the file for writing (truncate existing content)
    if ($handle !== false) {
        fwrite($handle, $ipv6); // Write the IPv6 address to the file
        fclose($handle); // Close the file handle
        return true;
    }
    return false; // Return false if file opening fails
}

// Function to save the IPv6 address to file
function saveIPv6Address($file, $ipv6) {
    //echo iswriteable($file) ? "is writable<br>" : "not writable<br>";
    return file_put_contents($file, $ipv6);
}

// Check if script is called with parameter to identify and save IPv6 address
if (isset($_GET['identify_ipv6'])) {
    // Get the IPv6 address from the HTTP request
    //echo ".";
    $client_ipv6 = $_GET['identify_ipv6'];
    if (saveIPv6Address($ipv6_file, $client_ipv6)) { echo "OK"; }
    else { echo "Not OK"; }
    echo "  ";
    echo $client_ipv6;

    // Save the IPv6 address to file
    if (filter_var("[$client_ipv6]", FILTER_VALIDATE_IP, FILTER_FLAG_IPV6)) {
        echo 'IPv6 address saved successfully!';
        saveIPv6Address($ipv6_file, $client_ipv6);
    } else {
        echo 'Invalid IPv6 address' + $client_ipv6;
    }
    echo "end";
    exit; // Stop script execution after saving IPv6 address
}

// Get the stored IPv6 address
$ipv6_address = getStoredIPv6Address($ipv6_file);

// If IPv6 address is not stored or not accessible, display link
if (!$ipv6_address) { // || !filter_var("[$ipv6_address]", FILTER_VALIDATE_IP, FILTER_FLAG_IPV6)) {
    echo '<!DOCTYPE html>
    <html>
    <head>
        <meta name="apple-mobile-web-app-capable" content="yes"></meta>
        <meta name="apple-mobile-web-app-status-bar-style" content="black"></meta>
        <META name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=0.3, maximum-scale=1.0"></META>
        <LINK rel=apple-touch-icon             href="favicon.png"></LINK>
        <LINK rel=apple-touch-icon-precomposed href="favicon.png"></LINK>

        <title>jc://birdhouse/</title>
    </head>
    <body style="background:#111111">
        <center>
        <h1 style="color:#EEEEEE">jc://birdhouse/</h1>
        <br/>&nbsp;
        <p style="color:#EEEEEE">
            <img src="bird.gif" style="width:250px;" /><br/>
            <br/>&nbsp;
            <br/>&nbsp;
            Got no address from birdhouse server yet.
        </p>
        </center>
    </body>
    </html>';
} else {
    // Display link with stored IPv6 address
    echo '<!DOCTYPE html>
    <html>
    <head>
        <meta name="apple-mobile-web-app-capable" content="yes"></meta>
        <meta name="apple-mobile-web-app-status-bar-style" content="black"></meta>
        <META name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=0.3, maximum-scale=1.0"></META>
        <LINK rel=apple-touch-icon             href="favicon.png"></LINK>
        <LINK rel=apple-touch-icon-precomposed href="favicon.png"></LINK>

        <title>jc://birdhouse/</title>
    </head>
    <body style="background:#111111">
        <center>
        <h1 style="color:#EEEEEE">jc://birdhouse/</h1>
        <br/>&nbsp;
        <p style="color:#EEEEEE">
            <a href="http://[' . $ipv6_address . ']:8000"><img src="bird.gif" style="width:250px;" /></a><br/>
            <br/>&nbsp;
            <br/>&nbsp;
            Click
            <a href="http://[' . $ipv6_address . ']:8000" style="color:yellow">here</a>
            to get to the birdhouse.
        </p>
        </center>
    </body>
    </html>';
}
?>
